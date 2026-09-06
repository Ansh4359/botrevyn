# Privacy Policy for BotRevyn

**Last Updated:** September 6, 2026

BotRevyn ("we", "our", or "us") provides an autonomous, multi-agent AI code review platform built as a GitHub App. This Privacy Policy describes how we collect, process, and safeguard data when you install and use BotRevyn on your GitHub repositories.

---

## 1. Information We Collect

When you install and interact with BotRevyn, we process the following categories of data:

- **Pull Request Metadata**: Repository full name, PR number, title, description, branch names, commit SHAs, and GitHub author username.
- **Code Diffs and Patches**: Unified file diffs and surrounding context lines necessary to evaluate the proposed code changes.
- **Account Identifiers**: Public GitHub username, user ID, and avatar URL when logging into the BotRevyn dashboard via GitHub OAuth.
- **Installation Identifiers**: GitHub App installation IDs and associated account names.

---

## 2. Information We NEVER Collect or Store

- **Full Source Code Repositories**: BotRevyn does not clone, download, or persist your entire repository.
- **Permanent Code Storage**: Pull request diffs are processed ephemerally in-memory and discarded immediately after review generation.
- **Secrets and Passwords**: We never collect or store your repository secrets, private credentials, or personal passwords.

---

## 3. Zero Model Training Guarantee

- **No AI Model Training**: Customer code, pull request diffs, and review feedback are **never used to train, retrain, or fine-tune** any public or private AI models.
- **Enterprise Data Protection**: External API processing (via Google Cloud Gemini Developer APIs) operates under enterprise confidentiality agreements with strict zero-data-retention terms.

---

## 4. How We Use Information

We use the collected information exclusively to:
- Generate automated code reviews, security scans, and test suggestions on your pull requests.
- Provide you with personal analytics and review history on the BotRevyn web dashboard.
- Authenticate authorized users via GitHub OAuth.

---

## 5. Data Retention and Erasure (GDPR / CCPA)

- **Review Metadata**: Aggregate review metrics (issue counts, timestamps, verdicts) are retained to populate your private dashboard.
- **Right to Erasure**: You can request complete deletion of your records at any time by contacting `privacy@botrevyn.com`.
- **App Uninstallation**: Uninstalling the BotRevyn GitHub App automatically disassociates and revokes all active repository access tokens.

---

## 6. Security

All data in transit is encrypted using industry-standard TLS 1.2/1.3. Webhook deliveries from GitHub are verified using HMAC-SHA256 signatures. Dashboard sessions are secured via short-lived JWT tokens and HTTP-only cookies.

---

## 7. Contact Us

If you have questions about this Privacy Policy or our data practices, please contact us:
- **Email**: `privacy@botrevyn.com`
- **GitHub Repository**: [https://github.com/Ansh4359/botrevyn](https://github.com/Ansh4359/botrevyn)
