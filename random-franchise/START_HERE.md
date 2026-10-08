# Put this app in your existing GitHub repository

You already have a GitHub repository and a Streamlit account. These files are the actual app code.

1. Download and extract `random-franchise.zip`.
2. Open the extracted `random-franchise` folder. You should see `app.py`, `requirements.txt`, `pages`, and `services`.
3. Open your existing repository on GitHub and choose **Add file → Upload files**.
4. Drag the folder's **contents** into the upload area, preserving subfolders. Upload the files, not the ZIP.
5. Enter a commit message such as `Add Random Franchise app` and choose **Commit changes**.
6. Confirm `app.py` and `requirements.txt` are at the repository's top level.
7. Open [Streamlit Community Cloud](https://share.streamlit.io/) and choose **Create app**, then the option for an app you already have.
8. Enter:

| Field | Value |
| --- | --- |
| Repository | Your GitHub username / repository name |
| Branch | `main`, or your actual branch |
| Main file path | `app.py` |
| Advanced settings → Python | `3.12` |

9. For password protection, add `app_password = "your-private-password"` to Streamlit's Secrets field. Choose your own password; keep it out of GitHub.
10. Click **Deploy**. Once the app opens, choose **Load Demo Franchise**, then **Open franchise dashboard**.

If you uploaded the enclosing folder, the main path is `random-franchise/app.py` instead. Uploading the contents directly is simpler.

Some browser uploads omit hidden folders. The app still runs without them, but to keep the theme, add `.streamlit/config.toml` through GitHub's **Add file → Create new file** and paste its contents from the ZIP. Add `.github/workflows/tests.yml` similarly for automated tests.

**Download a full backup from Settings after each session.** App data saves to SQLite, not back to GitHub. Streamlit Cloud's local files can disappear. If the app starts empty, restore your downloaded backup on Home before loading the demo. The README explains durable hosting and local recovery.

Local quick start after activating a Python virtual environment:

```bash
python -m pip install -r requirements-dev.txt
python -m streamlit run app.py
```
