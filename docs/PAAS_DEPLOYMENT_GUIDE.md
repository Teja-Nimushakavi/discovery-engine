# PaaS Deployment Guide (Option 1)

This guide walks you through deploying the `discovery-engine` using Vercel (Frontend), Render (API + Pipeline), and Supabase (PostgreSQL).

## 1. Database (Supabase)

Supabase offers a generous free tier for PostgreSQL.

1. Go to [Supabase](https://supabase.com/) and create an account/sign in.
2. Click **New Project**, select an organization, and give your project a name (e.g., `discovery-engine`).
3. Set a secure database password and choose a region close to your users.
4. Once provisioned, go to **Project Settings -> Database**.
5. Copy the **Connection String (URI)**. It will look like this:
   `postgresql://postgres.[YOUR_PROJECT_ID]:[YOUR_PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`
6. **Initialize the Schema:** Run your SQL migrations against this database using `psql` or DBeaver:
   ```bash
   psql "your-supabase-connection-string" -f storage/migrations/001_initial_schema.sql
   ```

## 2. API & Pipeline (Render)

We've prepared a `render.yaml` file in the root of your project to automate this via Infrastructure as Code.

1. Go to [Render](https://render.com/) and create an account.
2. Make sure your latest code (including the `render.yaml`) is pushed to your GitHub repository.
3. In Render, click **New -> Blueprint**.
4. Connect your GitHub account and select your `discovery-engine` repository.
5. Render will detect the `render.yaml` file and prompt you to create the two services: `discovery-engine-api` and `discovery-engine-pipeline`.
6. **Configure Environment Variables:**
   Render will ask you to provide the missing environment variables (because `sync: false` was set in the yaml):
   *   `DATABASE_URL`: Paste the Supabase Connection String.
   *   `GROQ_API_KEY`: Your Groq API key.
   *   `PINECONE_API_KEY`: Your Pinecone API key.
   *   `APIFY_API_TOKEN`: Your Apify token (if applicable).
7. Click **Apply**. 

*Note: The API can run on Render's Free tier, but the Cron Job (`discovery-engine-pipeline`) requires a paid plan (Starter, ~$7/mo). If you strictly want 100% free, you can remove the cron service from `render.yaml` and trigger `scripts/run_pipeline.py` using GitHub Actions instead.*

8. Once the API is deployed, copy its public URL (e.g., `https://discovery-engine-api.onrender.com`).

## 3. Frontend (Vercel)

Vercel is the easiest way to deploy a Vite React app.

1. Go to [Vercel](https://vercel.com/) and log in with GitHub.
2. Click **Add New -> Project**.
3. Import your `discovery-engine` repository.
4. **Important:** Change the "Root Directory" to `frontend`.
5. Vercel will automatically detect that you are using Vite and set the build command to `npm run build` and output directory to `dist`.
6. Add your Environment Variables:
   *   **Name:** `VITE_API_URL`
   *   **Value:** `https://discovery-engine-api.onrender.com` (Your Render API URL from Step 2)
7. Click **Deploy**.

## 4. Verification

1. Visit your new Vercel `.vercel.app` URL to see the React Dashboard.
2. Test an API endpoint via the Swagger UI at `https://discovery-engine-api.onrender.com/docs`.
3. Check the Render logs to ensure the pipeline runs successfully.
