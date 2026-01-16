## GCP Cloud Run Deployment (Backend)
Make sure the google-cloud-sdk is installed and configured on your local machine (https://docs.cloud.google.com/sdk/docs/install-sdk).


1. Login (from `crs-chatbot` root directory):
```bash
./google-cloud-sdk/bin/gcloud auth login
```
2. Verify project selection
```bash
./google-cloud-sdk/bin/gcloud config set project YOUR_PROJECT_ID
```
3. Make sure APIs are enabled:
```bash
./google-cloud-sdk/bin/gcloud services enable cloudbuild.googleapis.com

./google-cloud-sdk/bin/gcloud services enable run.googleapis.com
 ```
4. Build the application (from `crs-chatbot` root directory):
```bash
./google-cloud-sdk/bin/gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/adk-agent-service . 
```
5. Deployment (if you're doing this, you can ignore step 4 as Cloud Run will build it for you):
```bash
gcloud auth login
gcloud run deploy adk-agent-service --source .
```
If prompted, select the region (in this case: `eu-west1`) and allow unauthenticated invocations.
`gcloud config set run/region europe-west1`

## Deployment (via Cloud Run Console)
1. Go to the **[Cloud Run Console](https://console.cloud.google.com/run/overview)**.
2. Click **Create Service**.
3. **Container Image URL**: Click "Select" and find the image you just built (in the `gcr.io` or `google-container-registry` folder).
4. **Service Name**: adk-agent-service.
5. Region: us-central1 (or one close to you).
6. Authentication: Select "Allow unauthenticated invocations" (if you want it public).
7. Container, Networking, Security (The important part!). Click this dropdown to expand it.
   * Go to the Variables & Secrets tab. 
   * Click Add Variable. 
   * Manually add every Key/Value pair from your local .env file here. 
   * Click Create.
8. Once the deployment finishes (it takes about 30-60 seconds), Google will give you a Service URL (e.g., https://adk-agent-service-xyz-uc.a.run.app).

Test your health check endpoint:
https://YOUR-SERVICE-URL.run.app/health

If you get a 200 OK, your API is live!