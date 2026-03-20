# Deploying TalentOrbit to Render

Render is the perfect platform for Django because it supports persistent disks (for your media uploads like avatars and videos) and provides a free managed PostgreSQL database.

## Prerequisites
1. Push this code to a **GitHub repository** (can be private).
2. Create an account on [Render.com](https://render.com).

## Deployment Steps

Because I've added a `render.yaml` file (Infrastructure as Code), the entire deployment process is literally 3 clicks:

1. Go to your Render Dashboard and click **New > Blueprint**.
2. Connect your GitHub repository containing this code.
3. Render will automatically detect the `render.yaml` file. Click **Apply**.

That's it! Render will automatically create the PostgreSQL database, the persistent disk, and the web app, connect them all together, and run the build steps to install dependencies, apply migrations, and bootstrap the hosted demo accounts.

## Post-Deployment Checklist

Once the deployment finishes and your site is live, there's one critical step for security:

1. In your Render Dashboard, go to your Web Service (**talentorbit-web**).
2. Go to the **Environment** tab.
3. Add the following environment variables manually (we keep these out of GitHub for security):
   - `RAZORPAY_KEY_ID`: Your live Razorpay key
   - `RAZORPAY_KEY_SECRET`: Your live Razorpay secret
   - `EMAIL_URL`: Your Gmail SMTP string (e.g. `smtp://your-email@gmail.com:app-password@smtp.gmail.com:587/?tls=True`). If your SMTP username or password contains reserved URL characters, URL-encode them first.
   - `DEFAULT_FROM_EMAIL`: Use the same mailbox as your SMTP account, or an alias your provider explicitly allows (example: `TalentOrbit <your-email@gmail.com>`)
   - `PUBLIC_APP_URL`: Your canonical public site URL (for example `https://talentorbit-web.onrender.com` or your custom domain) so verification links use the correct host. The Blueprint now seeds the Onrender URL by default, but set your custom domain here if you use one.
   - `BOOTSTRAP_DEMO_DATA`: Leave this as `true` if you want the deployed site to include the demo admin, company, and user accounts that appear locally. Set it to `false` if you want a blank production database instead.
   - `CLOUDINARY_CLOUD_NAME`: Your free Cloudinary cloud name
   - `CLOUDINARY_API_KEY`: Your Cloudinary API key
   - `CLOUDINARY_API_SECRET`: Your Cloudinary API secret

*Note: The `SECRET_KEY` and `DATABASE_URL` are handled automatically by Render. By using Cloudinary, your media storage is now 100% free and permanent.*

Your app will be live at `https://talentorbit-web.onrender.com` (you can attach a custom domain in the Render settings).

When `BOOTSTRAP_DEMO_DATA=true`, the deploy creates a small hosted demo dataset so the public site and admin dashboards are not empty:

- `admin / demo1234`
- `techcorp / demo1234`
- `john_doe / demo1234`

After configuring email env vars, verify delivery from the deployed shell with `python manage.py check_email --recipient you@example.com`.
