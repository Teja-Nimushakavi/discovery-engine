# PaaS Deployment Guide (Railway + Vercel)

This guide walks you through deploying the `discovery-engine` entirely for **free** using Vercel (Frontend), Railway (API), Supabase (PostgreSQL), and GitHub Actions (Scheduled Pipeline).

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

## 2. API (Railway)

Railway is incredibly fast and has a great free tier for hosting Docker containers.

1. Go to [Railway](https://railway.app/) and log in with your GitHub account.
2. Click **New Project** -> **Deploy from GitHub repo**.
3. Select your `discovery-engine` repository.
4. **Important:** By default, Railway might try to build the root folder. You need to tell it where the Dockerfile is. 
   - Click on the newly created service in your Railway project dashboard.
   - Go to **Settings** -> **Build**.
   - Under **Builder**, ensure it is set to **Dockerfile**.
   - Set the **Dockerfile Path** to `api/Dockerfile`.
5. Go to the **Variables** tab for that service and click **New Variable**. Add these:
   *   `DATABASE_URL`: Paste the Supabase Connection String.
   *   `GROQ_API_KEY`: Your Groq API key.
   *   `PINECONE_API_KEY`: Your Pinecone API key.
   *   `APIFY_API_TOKEN`: Your Apify token.
6. Go to the **Networking** tab and click **Generate Domain**.
7. Copy this new public URL (e.g., `https://discovery-engine...up.railway.app`).

## 3. Scheduled Data Pipeline (GitHub Actions)

We will use **GitHub Actions** to run the pipeline for free. We have already included a `.github/workflows/pipeline.yml` file.

1. Go to your repository on **GitHub**.
2. Click on **Settings -> Secrets and variables -> Actions**.
3. Under the **Secrets** tab, click **New repository secret**.
4. Add the following secrets (the exact same values you used for Railway):
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
   *   **Value:** `https://your-railway-domain.up.railway.app` (Your Railway API URL from Step 2)
7. Click **Deploy**.

## 5. Verification

1. Visit your new Vercel `.vercel.app` URL to see the React Dashboard.
2. Test an API endpoint via the Swagger UI at `https://your-railway-domain.up.railway.app/docs`.
3. Check the GitHub Actions logs to ensure the pipeline runs successfully.
