import os
import io
import time
import logging
import requests
import zipfile
from django.conf import settings

logger = logging.getLogger(__name__)

class NetlifyDeployer:
    def __init__(self, portfolio):
        self.portfolio = portfolio
        self.netlify_token = settings.NETLIFY_TOKEN
        if not self.netlify_token:
            logger.error("NETLIFY_TOKEN is missing.")
            raise ValueError("NETLIFY_TOKEN is required for deployment")
        
        # Ensure site name is Netlify-compatible (lowercase, letters, numbers, hyphens)
        self.site_name = f"{portfolio.user.username}-site".lower().replace('_', '-')
        # Use MEDIA_ROOT setting correctly
        self.portfolio_path = os.path.join(settings.MEDIA_ROOT, 'portfolios', f"{portfolio.user.username}_{portfolio.template.name}")
        self.api_base_url = "https://api.netlify.com/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.netlify_token}"
        }
        logger.info(f"NetlifyDeployer initialized for path: {self.portfolio_path} and site name: {self.site_name}")

    def deploy(self):
        """Deploy the portfolio to Netlify by uploading a zip archive."""
        try:
            logger.info(f"Starting portfolio deployment for site: {self.site_name}")

            if not os.path.isdir(self.portfolio_path):
                logger.error(f"Portfolio directory not found: {self.portfolio_path}")
                raise FileNotFoundError(f"Portfolio directory not found: {self.portfolio_path}")
            
            logger.info("Getting or creating Netlify site...")
            site_id = self._get_or_create_site()
            if not site_id:
                 raise Exception("Could not get or create Netlify site.")
            logger.info(f"Using site ID: {site_id}")

            logger.info("Creating zip archive of the portfolio directory...")
            zip_buffer = self._zip_directory(self.portfolio_path)
            logger.info(f"Zip archive created in memory (Size: {zip_buffer.getbuffer().nbytes} bytes)")

            # Upload the zip file to start deployment
            logger.info("Uploading zip archive to Netlify...")
            deploy_headers = self.headers.copy()
            deploy_headers["Content-Type"] = "application/zip"
            
            upload_response = requests.post(
                f"{self.api_base_url}/sites/{site_id}/deploys",
                headers=deploy_headers,
                data=zip_buffer.getvalue()
            )
            upload_response.raise_for_status()
            deploy_details = upload_response.json()
            deploy_id = deploy_details.get('id')
            logger.info(f"Deployment initiated successfully. Deploy ID: {deploy_id}")

            # Wait for the deployment to complete
            logger.info("Waiting for deployment to finish processing...")
            final_state = self._wait_for_deployment(deploy_id)

            if final_state == 'ready':
                logger.info("Deployment successful and site is live.")
                self.portfolio.is_published = True
                self.portfolio.netlify_site_id = site_id
                self.portfolio.netlify_deploy_id = deploy_id
                self.portfolio.netlify_url = deploy_details.get('deploy_ssl_url') or deploy_details.get('deploy_url')
                self.portfolio.save()
                logger.info(f"Updated portfolio status to published. Site URL: {self.portfolio.netlify_url}")
                return self.portfolio.netlify_url
            else:
                logger.error(f"Netlify deployment failed or ended in state: {final_state}")
                raise Exception(f"Netlify deployment failed with state: {final_state}")

        except requests.exceptions.RequestException as req_e:
            logger.error(f"Netlify API request failed: {req_e}")
            if req_e.response is not None:
                 logger.error(f"Response status: {req_e.response.status_code}")
                 logger.error(f"Response body: {req_e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to deploy portfolio: {str(e)}", exc_info=True)
            raise

    def _get_or_create_site(self):
        """Get existing site ID or create a new one."""
        try:
            # List sites
            list_url = f"{self.api_base_url}/sites"
            logger.info(f"Listing sites via GET {list_url}")
            response = requests.get(list_url, headers=self.headers, params={'filter': 'all'})
            response.raise_for_status()
            sites = response.json()
            logger.info(f"Found {len(sites)} sites associated with the token.")

            # Check if site exists
            for site in sites:
                if site.get('name') == self.site_name:
                    logger.info(f"Found existing site '{self.site_name}' with ID: {site.get('id')}")
                    return site.get('id')

            # Create site if it doesn't exist
            logger.info(f"Site '{self.site_name}' not found. Creating new site...")
            create_url = f"{self.api_base_url}/sites"
            site_data = {'name': self.site_name}
            
            create_response = requests.post(create_url, headers=self.headers, json=site_data)
            
            if create_response.status_code == 422:
                 logger.error(f"Site name '{self.site_name}' might already be taken or invalid.")
                 time.sleep(2)
                 response = requests.get(list_url, headers=self.headers, params={'filter': 'all'})
                 response.raise_for_status()
                 sites = response.json()
                 for site in sites:
                     if site.get('name') == self.site_name:
                         logger.info(f"Found existing site '{self.site_name}' after creation conflict. ID: {site.get('id')}")
                         return site.get('id')
                 logger.error(f"Could not create or find site '{self.site_name}' after conflict.")
                 return None

            create_response.raise_for_status()
            new_site = create_response.json()
            logger.info(f"Created new site: {new_site.get('name')} with ID: {new_site.get('id')}")
            return new_site.get('id')

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting/creating Netlify site: {e}")
            if e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in _get_or_create_site: {e}", exc_info=True)
            return None

    def _zip_directory(self, path):
        """Creates a zip archive of a directory in memory."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # First, add the _headers file to set content type
            headers_content = """/*
  Content-Type: text/html; charset=utf-8
"""
            zf.writestr('_headers', headers_content)
            
            # Then add the index.html file at the root
            index_path = os.path.join(path, 'index.html')
            if os.path.exists(index_path):
                # Read the file content
                with open(index_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Ensure proper HTML content type
                zf.writestr('index.html', content)
            
            # Then add all other files maintaining their directory structure
            for root, _, files in os.walk(path):
                for file in files:
                    if file == 'index.html':  # Skip index.html as we already added it
                        continue
                    file_path = os.path.join(root, file)
                    # Calculate the relative path from the portfolio directory
                    rel_path = os.path.relpath(file_path, path)
                    # Ensure paths use forward slashes for web compatibility
                    rel_path = rel_path.replace('\\', '/')
                    
                    # Read the file content
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    
                    # Write the file content to the zip
                    zf.writestr(rel_path, content)
        
        buffer.seek(0)
        return buffer

    def _wait_for_deployment(self, deploy_id, timeout=300, interval=5):
        """Polls Netlify API to check deployment status."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                deploy_url = f"{self.api_base_url}/deploys/{deploy_id}"
                response = requests.get(deploy_url, headers=self.headers)
                response.raise_for_status()
                deploy_status = response.json()
                state = deploy_status.get('state')
                logger.info(f"Current deployment state: {state}")

                if state == 'ready':
                    return 'ready'
                elif state in ['error', 'failed']:
                    logger.error(f"Deployment failed. Status: {deploy_status}")
                    return state
                elif state == 'building' or state == 'uploading' or state == 'processing':
                    pass
                else:
                    logger.warning(f"Unknown deployment state encountered: {state}")

                time.sleep(interval)

            except requests.exceptions.RequestException as e:
                logger.error(f"Error polling deployment status: {e}")
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Unexpected error during polling: {e}", exc_info=True)
                return "polling_error"

        logger.error(f"Deployment polling timed out after {timeout} seconds.")
        return 'timeout' 