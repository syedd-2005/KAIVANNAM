# KAIVANNAM – கைவண்ணம்

**கைவினைக் கலைஞர்களின் கைவண்ணம் நம்ம ஆதரவில் மலரட்டும்**

A professional Streamlit + SQLite Indian handicraft marketplace demo covering whole-India craft discovery, customer shopping, artisan tools, multilingual UI, AI-assisted features, delivery tracking, reviews, material exchange and skill exchange.

## Included
- 120+ seeded Indian handicraft products
- One local image per craft type; no broken image cards
- SQLite database at `data/kaivannam.db`
- Customer and Seller/Artisan roles with separate navigation
- Login, quick demo login, registration and logout
- Search and filters by product/craft/state/region/material/artisan/category/price/style
- Wishlist, persistent cart, checkout, demo payment, orders and delivery timeline
- Reviews and ratings
- Craft stories and heritage map
- AI shopping assistant, AI image analyzer, Waste → Craft AI
- Pillow Photo Rescue
- Multilingual dashboard labels: English, Tamil, Hindi, Malayalam, Telugu, Kannada
- Browser voice recognition with text fallback
- Artisan material exchange / பண்டமாற்று and skill exchange
- Seller analytics, product upload, delete and order status updates
- Optional Groq integration; missing key never crashes the app

## Run in VS Code
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Demo login
- Customer: `customer01`
- Seller: `artisan01`

Quick Login intentionally uses the user ID only for the demo flow. Registration still stores a password hash in SQLite.

## Groq
Edit `.streamlit/secrets.toml`:
```toml
GROQ_API_KEY = "YOUR_API_KEY_HERE"
```
Without a real key the app shows **AI Demo Mode – Add GROQ_API_KEY to enable live AI** and continues working.

## Images
The ZIP contains local craft-themed fallback artwork so every seeded product has an image and the app works offline. These are **illustrative demo assets, not photographs of the named craft objects**. Replace/add authentic photos in `assets/products/` using the craft filename (for example `thanjavur_painting.jpg`). Seller-uploaded images are stored in the same folder.

## Database
The included SQLite database is already seeded. The app also creates/migrates its tables automatically if the database is missing.

## Deployment
For Streamlit Community Cloud, upload the repository and add `GROQ_API_KEY` under the app's Secrets settings if live AI is required. SQLite persistence on hosted instances should be treated as demo-level storage; a production marketplace should use managed database/object storage.


## Final shopping build
- Tamil-first voice shopping using Streamlit audio recording + Groq Whisper when `GROQ_API_KEY` is configured.
- Real shopping flow: cart → delivery address → offers/coupon → demo payment → order confirmation → delivery tracking → reorder.
- Customer accounts, seller tools, wishlist, reviews, AI assistant and artisan stories retained.
- The uploaded KAIVANNAM logo is stored at `assets/logo/logo.png`.
- Bundled illustrated/cartoon product placeholders are removed. Catalog cards use source-linked real craft photographs from the documented Wikimedia Commons references in `assets/products/REAL_IMAGE_SOURCES.md`.
- Payments are intentionally demo-only; no real card/UPI transaction is processed.

## Presentation-ready quick run
1. Extract the ZIP.
2. Open the `KAIVANNAM` folder.
3. Double-click `RUN_KAIVANNAM.bat` (or use `py -m streamlit run app.py`).
4. Demo customer: `customer01`.
5. Demo artisan: `artisan01`.
6. Demo password used by the database is `demo123` if a password field is added later; the current quick-login screen intentionally uses the demo ID for fast presentation.
7. For live Groq AI and Tamil speech recognition, put the real key in `.streamlit/secrets.toml` as `GROQ_API_KEY = "..."`. Without it, the app stays in AI Demo Mode and does not crash.

### Voice interaction
The Streamlit microphone control is intentionally used so the browser can request microphone permission. Click **Record / Stop** once to start and again to stop. With a valid Groq key, stopping the recording automatically transcribes it and opens Browse with the recognized request.
