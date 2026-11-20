# QuickLoot: food, grocery and household deal alerts

A lightweight, **free-to-run** Telegram notifier built for quick-commerce offers in India. It reads the latest posts in selected **public Telegram channels**, checks what the product actually is, and forwards only food, groceries and everyday household essentials to your personal Telegram chat.

**Examples that should alert:** ice cream cakes, brownies, chips, oats, rice, eggs, cooking oil, shampoo, detergent, toothpaste, Swiggy/Zomato food-order coupons, and BigBasket grocery cart-wide offers.

**Examples that should not alert:** washing machines, air fryers, smartphones, electronics, clothing, furniture, jewellery or generic shopping promotions without a qualifying product.

## How it works

1. Every ~5 minutes GitHub Actions downloads the **public preview pages** of channels in `config.json`.
2. It reads newly posted text and filters for the categories above. A retailer's name alone does **not** qualify a deal.
3. It checks `state/seen.json` to avoid repeats, including reposts with identical text across channels.
4. It sends qualifying alerts to your Telegram account, including the posted price/description, an offer link if present, and the original Telegram post.
5. The Actions workflow commits the updated state to the repository so future runs remember what they already handled.

This is **not** a live Swiggy/Blinkit price or stock tracker. Deals may depend on location, account, coupons, or stock. It does not place orders.

## Setup (GitHub, no paid hosting)

### 1. Make a bot

- Open [@BotFather](https://t.me/BotFather) on Telegram and send `/newbot`.
- Save the token. **Do not paste it in your repository or commit it to Git.**
- Open your new bot and send `/start`.
- To get your numeric chat ID, you can message [@userinfobot](https://t.me/userinfobot). (Alternative: call Telegram's `getUpdates` using your bot token after `/start`.)

### 2. Create a new GitHub repository

- Suggested name: `quickloot`.
- Select **Public** for free standard GitHub-hosted Actions. The source code and public-message IDs will be visible, but bot credentials should only be stored in GitHub Secrets.
- Upload all files from this folder, **including the hidden `.github` directory**. GitHub's website upload supports folder drag-and-drop; alternatively use Git locally.

### 3. Add GitHub Actions secrets

Repo > **Settings > Secrets and variables > Actions > New repository secret**:

| Name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | token from BotFather |
| `TELEGRAM_CHAT_ID` | your Telegram numeric chat ID |

If your repository has restrictive workflow permissions: **Settings > Actions > General > Workflow permissions > Read and write permissions**. The workflow needs permission to commit `state/seen.json` for duplicate protection.

### 4. Run your first test

- Visit **Actions > QuickLoot food & grocery alerts > Run workflow**.
- Enable `test_alert` and click **Run workflow**. You should receive one test Telegram message.
- Run the workflow **again** with `test_alert` off. That first normal run silently records currently visible posts as already seen, preventing a flood of old deal notifications.
- New matching posts after that will trigger alerts as the schedule runs.

### 5. Change your preferences

Edit `config.json`:

```json
{
  "channels": ["dealztrendz", "growdealzlootoffers"],
  "preferred_city": "Mumbai",
  "max_post_age_hours": 6,
  "max_alerts_per_run": 12
}
```

You can remove any noisy channel or add a **public** channel username. For more detailed filters, edit `quickloot/filtering.py`.

## Run on Windows / locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env with your bot token and chat ID
python -m quickloot --test-alert
python -m quickloot --dry-run
python -m quickloot
```

`--dry-run` fetches public messages and shows matches without sending or changing state. The first normal run only seeds previous post IDs. To intentionally alert on recent posts during setup, use `python -m quickloot --send-existing` (up to the configured maximum).

Tests:

```powershell
python -m unittest discover -s tests -v
```

## Known limitations

- **Not instant:** scheduled GitHub Actions can be late or occasionally skipped; the minimum schedule interval is 5 minutes. Flash offers might expire before you open them.
- **Source limitations:** Telegram public web previews are unofficial, return a limited number of posts and may change. Private channels cannot be read using this method. Image-only posts without captions are skipped.
- **X/Twitter is not connected:** scraping X is fragile and its official API may cost money. Public Telegram channels are a more practical free starting point.
- **Filter accuracy:** this is rule-based and may miss products whose names don't match the lists. It can also let through an irrelevant post. Refine the terms based on actual alerts.
- **City/stock:** `preferred_city` blocks only explicitly other-city-only posts. It cannot guarantee deals apply to your Mumbai PIN code or verify price in your app.
- **State commits:** every run that discovers new posts creates a bot commit to `state/seen.json`. A history of public-message IDs is kept in the repo. The oldest IDs are pruned automatically.
- **GitHub inactivity:** GitHub may disable scheduled Actions in a public repo after 60 days without activity. Re-enable in Actions if that occurs.

## Next upgrades

1. Better product classification (including product names from photos), and a feedback-based `/mute` feature.
2. Price thresholds and prioritization for unusually cheap deals (for example 70%+ discounts).
3. Additional public sources, and optional tracked-product searches.
4. An always-on polling worker on reliable infrastructure if five-minute GitHub scheduling proves too slow.

## Safety

Never commit your bot token, your private chat ID, or session cookies. Only read public posts, and do not automatically place orders. Treat retailer links posted by third parties as unverified until you open the official app.
