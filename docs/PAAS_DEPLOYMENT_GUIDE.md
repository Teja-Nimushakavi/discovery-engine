# PaaS Deployment Guide (Option 1)

This guide walks you through deploying the `discovery-engine` entirely for **free** using Vercel (Frontend), Render (API), Supabase (PostgreSQL), and GitHub Actions (Scheduled Pipeline).

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

## 2. API (Render)

We've prepared a `render.yaml` file in the root of your project to automate this via Infrastructure as Code.

1. Go to [Render](https://render.com/) and create an account.
2. Make sure your latest code (including the `render.yaml`) is pushed to your GitHub repository.
3. In Render, click **New -> Blueprint**.
4. Connect your GitHub account and select your `discovery-engine` repository.
5. Render will detect the `render.yaml` file and prompt you to create the service: `discovery-engine-api`.
6. **Configure Environment Variables:**
   Render will ask you to provide the missing environment variables (because `sync: false` was set in the yaml):
   *   `DATABASE_URL`: Paste the Supabase Connection String.
   *   `GROQ_API_KEY`: Your Groq API key.
   *   `PINECONE_API_KEY`: Your Pinecone API key.
   *   `APIFY_API_TOKEN`: Your Apify token (if applicable).
7. Click **Apply**.

8. Once the API is deployed, copy its public URL (e.g., `https://discovery-engine-api.onrender.com`).

## 3. Scheduled Data Pipeline (GitHub Actions)

Since cron jobs are paid on Render, we will use **GitHub Actions** to run the pipeline for free. We have already included a `.github/workflows/pipeline.yml` file.

1. Go to your repository on **GitHub**.
2. Click on **Settings -> Secrets and variables -> Actions**.
3. Under the **Secrets** tab, click **New repository secret**.
4. Add the following secrets (the same values you used for Render):
   *   `DATABASE_URL`
   *   `GROQ_API_KEY`
   *   `PINECONE_API_KEY`
   *   `APIFY_API_TOKEN`
5. The pipeline is scheduled to run every day at midnight (UTC). To test it immediately, go to the **Actions** tab in your GitHub repository, click on **Daily Data Pipeline** on the left sidebar, and click **Run workflow**.

## 4. Frontend (Vercel)

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

## 5. Verification

1. Visit your new Vercel `.vercel.app` URL to see the React Dashboard.
2. Test an API endpoint via the Swagger UI at `https://discovery-engine-api.onrender.com/docs`.
3. Check the Render logs to ensure the pipeline runs successfully.
