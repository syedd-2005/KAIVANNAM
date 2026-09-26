import base64
import hashlib
import io
import os
import re
import sqlite3
import textwrap
import urllib.parse
import urllib.request
import html as html_lib
import requests
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageEnhance

try:
    from groq import Groq
except Exception:
    Groq = None

try:
    import qrcode
except Exception:
    qrcode = None


# ============================================================
# APP SETUP
# ============================================================

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "data" / "kaivannam.db"
PRODUCT_DIR = APP_DIR / "assets" / "products"
LOGO_DIR = APP_DIR 

# UPI ID used to generate the payment QR code.
# Replace this with your real merchant UPI ID.
UPI_ID = "yourupi@upi"

# Tamil voice-search aliases.
# These are catalog-oriented synonyms, so spoken Tamil product names
# are matched against the English catalog data as well.
VOICE_ALIASES = {
    "பானை": ["pot", "clay pot", "earthen pot", "pottery", "terracotta", "ceramic"],
    "மண்பானை": ["clay pot", "earthen pot", "pottery", "terracotta", "pot"],
    "குடம்": ["pot", "water pot", "clay pot", "pottery", "terracotta"],
    "குடுவை": ["pot", "water pot", "clay pot", "pottery", "terracotta", "container"],
    "சாரி": ["sari", "saree", "textile", "silk", "cotton", "weaving", "handloom"],
    "சாரீ": ["sari", "saree", "textile", "silk", "cotton", "weaving", "handloom"],
    "சேலை": ["sari", "saree", "textile", "silk", "cotton", "weaving", "handloom"],
    "புடவை": ["sari", "saree", "textile", "silk", "cotton", "weaving", "handloom"],
    "ஓவியம்": ["painting", "art"],
    "பொம்மை": ["toy", "toys", "doll", "dolls"],
    "கூடை": ["basket", "basketry", "bamboo", "cane"],
    "மூங்கில்": ["bamboo", "basket", "cane"],
    "பிரம்பு": ["cane", "basket", "bamboo"],
    "பாய்": ["mat", "pattamadai", "grass", "korai"],
    "துணி": ["textile", "cotton", "silk", "weaving", "embroidery"],
    "பட்டுப் புடவை": ["sari", "saree", "silk", "textile", "weaving"],
    "பட்டு": ["silk", "sari", "saree", "textile", "weaving"],
    "கைவினை": ["craft", "handmade", "artisan", "handicraft"],
    "கைவினை பொருட்கள்": ["craft", "handmade", "artisan", "handicraft"],
    "கைவினைப் பொருட்கள்": ["craft", "handmade", "artisan", "handicraft"],
    "க்ராஃப்ட் பொருட்கள்": ["craft", "handmade", "artisan", "handicraft"],
    "கிராஃப்ட் பொருட்கள்": ["craft", "handmade", "artisan", "handicraft"],
    "க்ராஃப்ட்": ["craft", "handmade", "artisan", "handicraft"],
    "கிராஃப்ட்": ["craft", "handmade", "artisan", "handicraft"],
    "புடவைகள்": ["sari", "saree", "textile", "silk", "cotton", "weaving", "handloom"],
    "சேலைகள்": ["sari", "saree", "textile", "silk", "cotton", "weaving", "handloom"],
    "சாரிகள்": ["sari", "saree", "textile", "silk", "cotton", "weaving", "handloom"],
    "கூடைகள்": ["basket", "basketry", "bamboo", "cane"],
    "கூடைகள்": ["basket", "basketry", "bamboo", "cane"],
    "குடுவைகள்": ["pot", "vase", "water pot", "clay pot", "pottery", "terracotta", "container"],
    "குடவைகள்": ["pot", "vase", "water pot", "clay pot", "pottery", "terracotta", "container"],
    "பானைகள்": ["pot", "clay pot", "earthen pot", "pottery", "terracotta", "ceramic"],
    "மண்பானைகள்": ["clay pot", "earthen pot", "pottery", "terracotta", "pot"],
    "மண் பானைகள்": ["clay pot", "earthen pot", "pottery", "terracotta", "pot"],
    "தஞ்சாவூர் பொருட்கள்": ["thanjavur", "tanjore", "thanjavur painting", "thanjavur dolls", "tanjore metal relief"],
    "தஞ்சை பொருட்கள்": ["thanjavur", "tanjore", "thanjavur painting", "thanjavur dolls", "tanjore metal relief"],
    # Roman/English spellings that Whisper may return for Tamil speech.
    "panai": ["பானை", "pot", "clay pot", "earthen pot", "pottery", "terracotta", "ceramic"],
    "mannpanai": ["மண்பானை", "clay pot", "earthen pot", "pottery", "terracotta", "pot"],
    "kudam": ["குடம்", "pot", "water pot", "clay pot", "pottery", "terracotta"],
    "sari": ["சாரி", "சாரீ", "சேலை", "புடவை", "saree", "textile", "silk", "cotton", "weaving", "handloom"],
    "saree": ["சாரி", "சாரீ", "சேலை", "புடவை", "sari", "textile", "silk", "cotton", "weaving", "handloom"],
    "sorry": ["சாரி", "சாரீ", "சேலை", "புடவை", "sari", "saree", "textile", "silk", "cotton", "weaving"],
    "selai": ["சேலை", "சாரி", "சாரீ", "புடவை", "sari", "saree", "textile", "silk", "cotton", "weaving"],
    "pudavai": ["புடவை", "சேலை", "சாரி", "சாரீ", "sari", "saree", "textile", "silk", "cotton", "weaving"],
    "oviyam": ["ஓவியம்", "painting", "art"],
    "oodiyam": ["ஓவியம்", "painting", "art"],
    "koodai": ["கூடை", "basket", "basketry", "bamboo", "cane"],
    "bommai": ["பொம்மை", "toy", "toys", "doll", "dolls"],
    "paai": ["பாய்", "mat", "pattamadai", "grass", "korai"],
    "நகை": ["jewellery", "jewelry", "metal", "silver", "enamel"],
    "தோல்": ["leather", "leather craft"],
    "மரச்சிற்பம்": ["wood craft", "wood carving", "walnut wood", "sandalwood"],
    "மரம்": ["wood", "wood craft", "wood carving", "sandalwood"],
    "வெண்கலம்": ["bronze", "bell metal", "metal craft"],
    "பித்தளை": ["brass", "metal craft"],
    "களிமண்": ["clay", "pottery", "terracotta", "clay pot"],
    # Common English spellings/requests for Thanjavur (Tanjore) crafts.
    "tanjore": ["thanjavur", "tanjore", "thanjavur painting", "thanjavur dolls", "tanjore metal relief"],
    "thanjore": ["thanjavur", "tanjore", "thanjavur painting", "thanjavur dolls", "tanjore metal relief"],
    "tanjavur": ["thanjavur", "tanjore", "thanjavur painting", "thanjavur dolls", "tanjore metal relief"],
    "thanjavur": ["thanjavur", "tanjore", "thanjavur painting", "thanjavur dolls", "tanjore metal relief"],
}

# Common Tamil/English phonetic variants that Whisper may return for craft words.
# These are normalized before the Browse search so spoken Tamil such as
# "பாணை", "குடைவை", "panai", or "kuduvai" maps to the intended catalog terms.
VOICE_NORMALIZATION = {
    "பாணை": "பானை",
    "பான": "பானை",
    "பனாய்": "பானை",
    "panai": "பானை",
    "pannai": "பானை",
    "paanai": "பானை",
    "குடைவை": "குடுவை",
    "குடவை": "குடுவை",
    "குடுவை": "குடுவை",
    "kuduvai": "குடுவை",
    "kudavai": "குடுவை",
    "kuduvay": "குடுவை",
    "குடம்": "குடம்",
    "புடவைகள்": "புடவை",
    "சேலைகள்": "சேலை",
    "சாரிகள்": "சாரி",
    "கூடைகள்": "கூடை",
    "குடுவைகள்": "குடுவை",
    "குடவைகள்": "குடுவை",
    "மண்பானைகள்": "மண்பானை",
    "மண் பானைகள்": "மண் பானை",
    "தஞ்சாவூர்": "தஞ்சாவூர்",
    "தஞ்சை": "தஞ்சாவூர்",
}



# Common Whisper hallucinations on silence/background noise.
VOICE_HALLUCINATIONS = {
    "thank you for watching",
    "thanks for watching",
    "thank you for watching this video",
    "thanks for watching this video",
    "thank you",
    "thanks",
    "please subscribe",
    "like and subscribe",
    "subscribe to my channel",
    "please like and subscribe",
    "thanks for watching and please subscribe",
}

# Very short Whisper outputs that are commonly produced from silence/noise.
VOICE_NOISE_PHRASES = {
    "thank you", "thanks", "okay", "ok", "you", "yeah", "yes", "no",
    "subscribe", "please",
}


PRODUCT_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

st.set_page_config(
    page_title="KAIVANNAM – கைவண்ணம்",
    page_icon="logo.png",
    layout="wide"
)


# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>

:root{
    --maroon:#6b2337;
    --terracotta:#b85c38;
    --gold:#c69b45;
    --cream:#fbf5e8;
    --brown:#3d2b24;
    --green:#356b50;
}

.stApp{
    background:var(--cream);
    color:var(--brown);
}

[data-testid="stSidebar"]{
    background:#fffaf0 !important;
    border-right:1px solid #eadbc4;
}

[data-testid="stSidebar"] h2{
    color:var(--maroon) !important;
    text-align:center;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label{
    color:var(--brown) !important;
    font-weight:700 !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"]{
    gap:7px !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label{
    background:#fffdf8 !important;
    border:1px solid #eadbc9 !important;
    border-radius:11px !important;
    padding:9px 11px !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked){
    background:#6b2337 !important;
    border-color:#6b2337 !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) p{
    color:#ffffff !important;
}

[data-testid="stMainBlockContainer"]{
    max-width:1400px;
    padding-top:1.5rem;
    padding-bottom:3rem;
}

.block-container{
    padding-left:2.5rem !important;
    padding-right:2.5rem !important;
}

.hero{
    background:linear-gradient(135deg,#fff8ea,#f0dcc2);
    border:1px solid #ead3b5;
    border-radius:24px;
    padding:32px;
    margin-bottom:22px;
}

.hero h1{
    color:var(--maroon);
    font-size:44px;
    margin:0;
}

.hero p{
    font-size:18px;
    margin:6px 0;
}

.card{
    background:#fff;
    border:1px solid #eadbc9;
    border-radius:18px;
    padding:12px;
    box-shadow:0 5px 18px rgba(75,45,30,.07);
    height:100%;
}

.card img{
    width:100%;
    height:205px;
    object-fit:cover;
    border-radius:14px;
}

.price{
    color:var(--maroon);
    font-size:21px;
    font-weight:800;
}

.small{
    color:#78685d;
    font-size:13px;
}

.notice{
    padding:12px 16px;
    border-radius:12px;
    background:#fff3d8;
    border:1px solid #ecd39e;
}

.shopbar{
    background:#ffffff;
    border:1px solid #eadbc9;
    border-radius:16px;
    padding:10px 14px;
    margin-bottom:18px;
}

.address-card{
    background:#fff;
    border:1px solid #eadbc9;
    border-radius:14px;
    padding:16px;
}

.order-total{
    background:#fff8ea;
    border:1px solid #e6c98f;
    border-radius:16px;
    padding:18px;
}

.voice-panel{
    background:linear-gradient(135deg,#fffdf8,#f5ead9);
    border:1px solid #ead3b5;
    border-radius:22px;
    padding:22px 24px;
    margin:10px 0 20px 0;
}

.voice-status{
    background:#fff;
    border:1px solid #eadbc9;
    border-radius:14px;
    padding:13px 16px;
}

.quick-card{
    background:#fff;
    border:1px solid #eadbc9;
    border-radius:16px;
    padding:15px 16px;
    min-height:115px;
}

.skill-card{
    background:#fff;
    border:1px solid #eadbc9;
    border-radius:16px;
    padding:18px;
    margin-bottom:12px;
}

.map-note{
    background:#fff8ea;
    border:1px solid #e6c98f;
    border-radius:14px;
    padding:14px;
    margin-bottom:15px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# CONSTANTS
# ============================================================

STATUSES = [
    "Order Placed",
    "Artisan Accepted",
    "Craft Being Prepared",
    "Packed",
    "Shipped",
    "Out for Delivery",
    "Delivered"
]

LANGS = [
    "English",
    "தமிழ்",
    "हिन्दी",
    "മലയാളം",
    "తెలుగు",
    "ಕನ್ನಡ"
]


# ============================================================
# CRAFT DATA
# ============================================================

CRAFTS = [
("Thanjavur Painting","Tamil Nadu","Thanjavur","Painting","Canvas, gold foil"),
("Thanjavur Dolls","Tamil Nadu","Thanjavur","Toys","Wood, papier-mâché"),
("Swamimalai Bronze","Tamil Nadu","Kumbakonam","Metal Craft","Bronze"),
("Pattamadai Mat","Tamil Nadu","Tirunelveli","Textiles","Korai grass"),
("Mahabalipuram Stone Craft","Tamil Nadu","Chengalpattu","Stone Craft","Granite"),
("Chettinad Craft","Tamil Nadu","Sivaganga","Home Decor","Wood, brass"),
("Tamil Terracotta","Tamil Nadu","Villupuram","Pottery","Terracotta clay"),
("Palm Leaf Craft","Tamil Nadu","Thanjavur","Eco-friendly Crafts","Palm leaf"),

("Aranmula Mirror","Kerala","Pathanamthitta","Home Decor","Bell metal"),
("Kerala Coir Craft","Kerala","Alappuzha","Eco-friendly Crafts","Coir"),
("Nettur Petti","Kerala","Kannur","Wood Craft","Wood, brass"),
("Kerala Bell Metal","Kerala","Thrissur","Metal Craft","Bell metal"),

("Mysore Painting","Karnataka","Mysuru","Painting","Wood, gold leaf"),
("Channapatna Toys","Karnataka","Ramanagara","Toys","Lacquered wood"),
("Sandalwood Craft","Karnataka","Mysuru","Wood Craft","Sandalwood"),
("Kasuti Embroidery","Karnataka","Dharwad","Embroidery","Cotton thread"),

("Kalamkari","Andhra Pradesh","Machilipatnam","Textiles","Cotton"),
("Kondapalli Toys","Andhra Pradesh","NTR district","Toys","Soft wood"),

("Cheriyal Painting","Telangana","Siddipet","Painting","Natural pigments"),
("Nirmal Painting","Telangana","Nirmal","Painting","Wood, natural pigments"),
("Pembarthi Metal Craft","Telangana","Jangaon","Metal Craft","Brass"),

("Blue Pottery","Rajasthan","Jaipur","Pottery","Quartz, glaze"),
("Bagru Block Printing","Rajasthan","Bagru","Textiles","Cotton, natural dye"),
("Lac Craft","Rajasthan","Jaipur","Home Decor","Lac"),
("Rajasthani Puppets","Rajasthan","Jaipur","Toys","Wood, textile"),
("Meenakari","Rajasthan","Jaipur","Jewellery","Metal, enamel"),

("Kutch Embroidery","Gujarat","Kutch","Embroidery","Cotton, mirrors"),
("Bandhani","Gujarat","Kutch","Textiles","Silk, cotton"),
("Rogan Art","Gujarat","Kutch","Painting","Castor oil pigment"),
("Dhokra Gujarat","Gujarat","Chhota Udaipur","Metal Craft","Bell metal"),
("Ajrakh Printing","Gujarat","Kutch","Textiles","Natural dyes"),

("Kantha","West Bengal","Murshidabad","Embroidery","Cotton"),
("Dokra Bengal","West Bengal","Bikna","Metal Craft","Bell metal"),
("Bengal Terracotta","West Bengal","Bishnupur","Pottery","Terracotta"),
("Shantiniketan Leather Craft","West Bengal","Birbhum","Leather Craft","Leather"),
("Baluchari Weaving","West Bengal","Bishnupur","Textiles","Silk"),

("Pattachitra","Odisha","Puri","Painting","Cloth, natural pigments"),
("Odisha Silver Filigree","Odisha","Cuttack","Jewellery","Silver"),
("Odisha Stone Carving","Odisha","Puri","Stone Craft","Stone"),
("Odisha Applique","Odisha","Pipili","Textiles","Cotton"),
("Odisha Dhokra","Odisha","Dhenkanal","Metal Craft","Bell metal"),

("Madhubani Painting","Bihar","Madhubani","Painting","Natural pigments"),
("Sikki Craft","Bihar","Madhubani","Eco-friendly Crafts","Sikki grass"),
("Sujuni Embroidery","Bihar","Muzaffarpur","Embroidery","Cotton"),

("Kashmiri Papier-Mâché","Jammu & Kashmir","Srinagar","Home Decor","Paper pulp"),
("Walnut Wood Carving","Jammu & Kashmir","Srinagar","Wood Craft","Walnut wood"),
("Kashmiri Embroidery","Jammu & Kashmir","Srinagar","Embroidery","Wool, silk"),
("Kashmir Carpet Weaving","Jammu & Kashmir","Srinagar","Textiles","Wool, silk"),

("Assam Bamboo Craft","Assam","Guwahati","Bamboo & Cane","Bamboo"),
("Assam Cane Craft","Assam","Barpeta","Bamboo & Cane","Cane"),
("Muga Silk Craft","Assam","Sivasagar","Textiles","Muga silk"),

("Northeast Weaving","Nagaland","Kohima","Textiles","Cotton, wool"),
("Tripura Bamboo Craft","Tripura","Agartala","Bamboo & Cane","Bamboo"),
("Manipur Pottery","Manipur","Imphal","Pottery","Clay"),

("Himachal Wool Craft","Himachal Pradesh","Kullu","Textiles","Wool"),
("Ringaal Craft","Uttarakhand","Almora","Bamboo & Cane","Ringaal bamboo"),
("Lucknow Chikankari","Uttar Pradesh","Lucknow","Embroidery","Cotton"),
("Varanasi Silk Weaving","Uttar Pradesh","Varanasi","Textiles","Silk"),
("Phulkari","Punjab","Patiala","Embroidery","Silk, cotton"),
("Goa Coconut Craft","Goa","Panaji","Eco-friendly Crafts","Coconut shell"),
("Warli Art","Maharashtra","Palghar","Painting","Natural pigments"),
("Paithani","Maharashtra","Paithan","Textiles","Silk, zari"),
("Bastar Bell Metal","Chhattisgarh","Bastar","Metal Craft","Bell metal"),
("Sohrai Art","Jharkhand","Hazaribagh","Painting","Earth pigments"),
("Andhra Leather Puppets","Andhra Pradesh","Nimmalakunta","Toys","Leather"),
("Sambalpuri Weaving","Odisha","Sambalpur","Textiles","Cotton"),
("Kullu Shawl","Himachal Pradesh","Kullu","Textiles","Wool"),
("Lepcha Weaving","Sikkim","Gangtok","Textiles","Cotton, wool"),
("Bamboo Basketry","Meghalaya","Shillong","Bamboo & Cane","Bamboo"),
("Mizo Weaving","Mizoram","Aizawl","Textiles","Cotton"),
("Naga Bead Craft","Nagaland","Kohima","Jewellery","Glass beads"),
("Tanjore Metal Relief","Tamil Nadu","Thanjavur","Metal Craft","Brass"),
("Pipli Applique","Odisha","Pipili","Textiles","Cotton"),
("Kutch Leather Craft","Gujarat","Kutch","Leather Craft","Leather"),
("Kashmiri Crewel","Jammu & Kashmir","Srinagar","Embroidery","Wool"),
]


VARIANTS = [
    "Heritage Edition",
    "Artisan Signature",
    "Traditional Decor Piece",
    "Contemporary Heritage",
    "Festival Collection",
    "Collector's Edition"
]

ARTISANS = [
    "Lakshmi","Meenakshi","Ravi","Sreedevi","Arun",
    "Fatima","Maya","Kiran","Yusuf","Bikash",
    "Anita","Sanjay","Revathi","Asha","Rahul"
]


# ============================================================
# REAL IMAGE URLS
# ============================================================

REAL_IMAGE_URLS = {
    "Thanjavur Painting":
        "https://upload.wikimedia.org/wikipedia/commons/f/ff/Thanjavur_Painting.jpg",

    "Pattachitra":
        "https://upload.wikimedia.org/wikipedia/commons/2/2a/Pattachitra_art.jpg",

    "Kondapalli Toys":
        "https://upload.wikimedia.org/wikipedia/commons/d/d0/Kondapalli_toys.jpg",

    "Aranmula Mirror":
        "https://upload.wikimedia.org/wikipedia/commons/1/13/Aranmula_Mirrors.jpg",

    "Blue Pottery":
        "https://upload.wikimedia.org/wikipedia/commons/5/5e/Blue_pottery_from_Jaipur.jpg",

    "Kashmiri Papier-Mâché":
        "https://upload.wikimedia.org/wikipedia/commons/2/23/Papier_mache_goods%2C_Kashmir_%288141417742%29.jpg",

    "Kalamkari":
        "https://upload.wikimedia.org/wikipedia/commons/5/5d/Kalamkari_at_its_best.jpg",

    "Phulkari":
        "https://upload.wikimedia.org/wikipedia/commons/d/da/Phulkari_%28shawl%29_from_India%2C_Honolulu_Museum_of_Art_3585.JPG",

    "Bandhani":
        "https://upload.wikimedia.org/wikipedia/commons/8/8a/Bandhani.jpg",

    "Assam Bamboo Craft":
        "https://upload.wikimedia.org/wikipedia/commons/6/6a/Innovative_Bamboo_Crafts_of_Assam.jpg",

    "Sandalwood Craft":
        "https://upload.wikimedia.org/wikipedia/commons/3/30/Sandalwood_arts_store_in_Mysore%2C_Karnataka_%282025%29_02.jpg",

    "Odisha Silver Filigree":
        "https://upload.wikimedia.org/wikipedia/commons/1/13/Silver_Filigree_Work.jpg",

    "Paithani":
        "https://upload.wikimedia.org/wikipedia/commons/0/03/Paithani_Bridal_Sari_LACMA_M.75.4.23_%282_of_2%29.jpg",

    "Bastar Bell Metal":
        "https://upload.wikimedia.org/wikipedia/commons/4/45/Dokra_from_tribes_of_Bastar_DSCN1172_01.jpg",

    "Dhokra Gujarat":
        "https://upload.wikimedia.org/wikipedia/commons/4/45/Dokra_from_tribes_of_Bastar_DSCN1172_01.jpg",

    "Dokra Bengal":
        "https://upload.wikimedia.org/wikipedia/commons/4/45/Dokra_from_tribes_of_Bastar_DSCN1172_01.jpg",

    "Odisha Dhokra":
        "https://upload.wikimedia.org/wikipedia/commons/4/45/Dokra_from_tribes_of_Bastar_DSCN1172_01.jpg",

    "Pipli Applique":
        "https://upload.wikimedia.org/wikipedia/commons/a/a5/Pipli_4.jpg",

    "Sikki Craft":
        "https://upload.wikimedia.org/wikipedia/commons/0/0f/Sikki_Grass_Craft_by_artisan_Nazda_Khatun_of_Bihar_01.jpg",

    "Madhubani Painting":
        "https://upload.wikimedia.org/wikipedia/commons/f/fa/Madhubani_painting.jpg",

    "Warli Art":
        "https://upload.wikimedia.org/wikipedia/commons/a/a3/Warli_painting.jpg",

    "Kantha":
        "https://upload.wikimedia.org/wikipedia/commons/3/39/Kantha_embroidery.jpg",

    "Kutch Embroidery":
        "https://upload.wikimedia.org/wikipedia/commons/e/e1/Kutchi_Embroidery.png",

    "Lucknow Chikankari":
        "https://upload.wikimedia.org/wikipedia/commons/0/05/Chikankari_of_lucknow.jpg",
}


REAL_CATEGORY_URLS = {
    "Painting": REAL_IMAGE_URLS["Madhubani Painting"],
    "Textiles": REAL_IMAGE_URLS["Bandhani"],
    "Embroidery": REAL_IMAGE_URLS["Kutch Embroidery"],
    "Weaving": REAL_IMAGE_URLS["Paithani"],
    "Toys": REAL_IMAGE_URLS["Kondapalli Toys"],
    "Pottery": REAL_IMAGE_URLS["Blue Pottery"],
    "Metal Craft": REAL_IMAGE_URLS["Dhokra Gujarat"],
    "Jewellery": REAL_IMAGE_URLS["Odisha Silver Filigree"],
    "Bamboo & Cane": REAL_IMAGE_URLS["Assam Bamboo Craft"],
    "Eco-friendly Crafts": REAL_IMAGE_URLS["Assam Bamboo Craft"],
    "Wood Craft": REAL_IMAGE_URLS["Sandalwood Craft"],
    "Home Decor": REAL_IMAGE_URLS["Sandalwood Craft"],
    "Stone Craft": REAL_IMAGE_URLS["Blue Pottery"],
    "Leather Craft": REAL_IMAGE_URLS["Kutch Embroidery"],
}


# ============================================================
# DATABASE
# ============================================================

def db():
    con = sqlite3.connect(DB_PATH, timeout=20)
    con.row_factory = sqlite3.Row
    return con


def hash_pw(p):
    return hashlib.sha256(p.encode()).hexdigest()


def dictrow(r):
    return dict(r) if r is not None else None


def q(sql, params=()):
    con = db()
    rows = con.execute(sql, params).fetchall()
    con.close()
    return rows


def one(sql, params=()):
    rows = q(sql, params)
    return rows[0] if rows else None


def exec_sql(sql, params=()):
    con = db()
    cur = con.execute(sql, params)
    con.commit()
    last = cur.lastrowid
    con.close()
    return last


def keyify(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


# ============================================================
# TRANSLATION SYSTEM
# ============================================================

TRANSLATIONS = {

"தமிழ்": {

"Home":"முகப்பு",
"Browse":"கைவினைப் பொருட்கள்",
"Product Details":"பொருள் விவரங்கள்",
"Wishlist":"விருப்பப் பட்டியல்",
"Cart":"கூடை",
"Checkout":"பணம் செலுத்துதல்",
"Orders":"எனது ஆர்டர்கள்",
"Craft Stories":"கைவினைக் கதைகள்",
"Heritage Map":"பாரம்பரிய வரைபடம்",
"AI Image Analyzer":"AI பட ஆய்வாளர்",
"AI Shopping Assistant":"AI ஷாப்பிங் உதவியாளர்",
"Voice Assistant":"குரல் உதவியாளர்",
"Profile":"சுயவிவரம்",
"Seller Dashboard":"விற்பனையாளர் டாஷ்போர்டு",
"My Products":"எனது பொருட்கள்",
"Add Product":"பொருள் சேர்க்க",
"Seller Orders":"விற்பனையாளர் ஆர்டர்கள்",
"AI Photo Rescue":"AI புகைப்பட மேம்பாடு",
"Waste → Craft AI":"கழிவு → கைவினை AI",
"Material Exchange":"பொருள் பரிமாற்றம்",
"Skill Exchange":"திறன் பரிமாற்றம்",
"Logout":"வெளியேறு",

"Navigate":"வழிசெலுத்தல்",
"Quick Login":"விரைவு உள்நுழைவு",
"Register":"பதிவு",
"User ID":"பயனர் ID",
"Role":"பங்கு",
"Customer":"வாடிக்கையாளர்",
"Seller / Artisan":"விற்பனையாளர் / கைவினைக் கலைஞர்",
"Continue":"தொடரவும்",
"Name":"பெயர்",
"Password":"கடவுச்சொல்",
"Confirm Password":"கடவுச்சொல்லை உறுதிப்படுத்தவும்",
"Create Account":"கணக்கை உருவாக்கவும்",

"Discover India Through Its Crafts":
"இந்தியாவை அதன் கைவினைகள் மூலம் கண்டறியுங்கள்",

"Handmade traditions, regional stories and artisan-made products in one marketplace.":
"கைவினைப் பாரம்பரியங்கள், பிராந்தியக் கதைகள் மற்றும் கலைஞர்கள் உருவாக்கிய பொருட்கள் ஒரே சந்தையில்.",

"Quick Actions":"விரைவு செயல்கள்",
"Shop Crafts":"கைவினைப் பொருட்களை வாங்குங்கள்",
"AI Shopping":"AI ஷாப்பிங்",
"Tamil Voice Search":"தமிழ் குரல் தேடல்",
"My Cart":"எனது கூடை",
"My Orders":"எனது ஆர்டர்கள்",
"Open":"திறக்கவும்",

"Featured Crafts":"சிறப்பு கைவினைகள்",
"Explore by State":"மாநில வாரியாக தேடுங்கள்",
"Craft Products":"கைவினைப் பொருட்கள்",
"States / Regions":"மாநிலங்கள் / பகுதிகள்",
"Craft Traditions":"கைவினைப் பாரம்பரியங்கள்",
"Artisans":"கைவினைக் கலைஞர்கள்",

"Search product, craft, state, region, material or artisan":
"பொருள், கைவினை, மாநிலம், பகுதி, பொருள் அல்லது கலைஞரைத் தேடுங்கள்",

"State":"மாநிலம்",
"Craft":"கைவினை",
"Category":"வகை",
"Style":"பாணி",
"All":"அனைத்தும்",
"Traditional":"பாரம்பரியம்",
"Contemporary":"நவீனம்",
"Minimum price":"குறைந்தபட்ச விலை",
"Maximum price":"அதிகபட்ச விலை",

"Your Cart":"உங்கள் கூடை",
"Quantity":"அளவு",
"Remove":"நீக்கு",
"Price Details":"விலை விவரங்கள்",
"Items":"பொருட்கள்",
"Subtotal":"மொத்தம்",
"Delivery":"டெலிவரி",
"FREE":"இலவசம்",
"Proceed to Checkout →":"பணம் செலுத்தச் செல்லவும் →",
"Continue Shopping":"தொடர்ந்து வாங்குங்கள்",

"Checkout":"பணம் செலுத்துதல்",
"Delivery Address":"டெலிவரி முகவரி",
"Saved addresses":"சேமிக்கப்பட்ட முகவரிகள்",
"+ Add a new address":"+ புதிய முகவரி",
"Full Name":"முழுப் பெயர்",
"Mobile Number":"மொபைல் எண்",
"House / Flat / Street":"வீடு / Flat / தெரு",
"Area / Locality (optional)":"பகுதி / உள்ளூர் (விருப்பம்)",
"City":"நகரம்",
"State":"மாநிலம்",
"PIN Code":"PIN குறியீடு",
"Landmark (optional)":"அடையாள இடம் (விருப்பம்)",
"Save this address for future orders":
"இந்த முகவரியை அடுத்த ஆர்டர்களுக்காக சேமிக்கவும்",
"Continue to Payment":"பணம் செலுத்த தொடரவும்",

"Order Summary":"ஆர்டர் சுருக்கம்",
"Offers":"சலுகைகள்",
"Apply coupon":"கூப்பனைப் பயன்படுத்தவும்",
"No coupon":"கூப்பன் இல்லை",
"Payment":"பணம் செலுத்துதல்",
"Choose payment method":"பணம் செலுத்தும் முறையைத் தேர்வு செய்யவும்",
"UPI":"UPI",
"Debit / Credit Card":"Debit / Credit Card",
"Net Banking":"Net Banking",
"Cash on Delivery":"பொருள் வந்தபின் பணம்",
"Place Order":"ஆர்டர் செய்யவும்",

"My Orders":"எனது ஆர்டர்கள்",
"Start Shopping":"ஷாப்பிங் தொடங்கவும்",
"Buy these again":"மீண்டும் வாங்கவும்",

"The Story Behind This Craft":"இந்த கைவினையின் கதை",
"Origin":"தோற்றம்",
"History & tradition":"வரலாறு மற்றும் பாரம்பரியம்",
"Artisan tradition":"கலைஞர் பாரம்பரியம்",
"Customer Reviews":"வாடிக்கையாளர் மதிப்புரைகள்",
"Submit Review":"மதிப்புரையை சமர்ப்பிக்கவும்",

"Craft Heritage Map":"இந்திய கைவினைப் பாரம்பரிய வரைபடம்",
"India Craft Heritage Map":
"இந்திய கைவினைப் பாரம்பரிய வரைபடம்",
"Only Indian craft heritage locations are shown on this map.":
"இந்த வரைபடத்தில் இந்திய கைவினைப் பாரம்பரிய இடங்கள் மட்டுமே காட்டப்படுகின்றன.",

"Ask in English, தமிழ், हिन्दी, മലയാളം, తెలుగు or ಕನ್ನಡ":
"English, தமிழ், हिन्दी, മലയാളം, తెలుగు அல்லது ಕನ್ನಡ மொழியில் கேளுங்கள்",
"Find Crafts":"கைவினைகளைத் தேடுங்கள்",
"Matching products from SQLite catalog":
"SQLite பட்டியலில் பொருந்தும் பொருட்கள்",

"Upload a craft/product image":
"கைவினை / பொருளின் படத்தை பதிவேற்றவும்",

"Voice language":"குரல் மொழி",
"Record / Stop":"பதிவு / நிறுத்து",
"Type your request":"உங்கள் தேடலை உள்ளிடுங்கள்",
"Search Request":"தேடலைத் தொடங்குங்கள்",

"Language":"மொழி",
"Save Language":"மொழியைச் சேமிக்கவும்",

"Artisan Dashboard":"கைவினைக் கலைஞர் டாஷ்போர்டு",
"Welcome":"வரவேற்கிறோம்",
"My Products":"எனது பொருட்கள்",
"Revenue":"வருமானம்",
"Average Rating":"சராசரி மதிப்பீடு",
"Wishlist":"விருப்பங்கள்",

"Add Product":"பொருள் சேர்க்க",
"Product name":"பொருளின் பெயர்",
"Craft type":"கைவினை வகை",
"District / Region":"மாவட்டம் / பகுதி",
"Material":"பயன்படுத்திய பொருள்",
"Price (₹)":"விலை (₹)",
"Stock":"இருப்பு",
"Description":"விளக்கம்",
"Craft story":"கைவினைக் கதை",
"Product image":"பொருள் படம்",
"Save Product":"பொருளைச் சேமிக்கவும்",

"Seller Orders":"விற்பனையாளர் ஆர்டர்கள்",
"Update status":"நிலையை மாற்றவும்",
"Save status":"நிலையைச் சேமிக்கவும்",

"AI Photo Rescue":"AI புகைப்பட மேம்பாடு",
"Upload a product photo":"பொருளின் புகைப்படத்தை பதிவேற்றவும்",
"Before":"முன்",
"After":"பின்",

"Waste → Craft AI":"கழிவு → கைவினை AI",
"Leftover material":"மீதமுள்ள பொருள்",
"Suggest Craft Ideas":"கைவினை யோசனைகளைப் பரிந்துரைக்கவும்",

"Material Exchange":"கைவினைப் பொருள் பரிமாற்றம்",
"List Material":"பொருளை பட்டியலிடு",
"Browse & Request":"தேடி கோரிக்கை அனுப்பு",
"Material offered":"வழங்கும் பொருள்",
"Quantity":"அளவு",
"Location":"இடம்",
"Wanted material":"தேவைப்படும் பொருள்",
"Publish":"வெளியிடு",
"Send Exchange Request":"பரிமாற்ற கோரிக்கை அனுப்பு",

"Skill Exchange":"திறன் பரிமாற்றம்",
"Skill Exchange Hub":"கைவினை திறன் பரிமாற்ற மையம்",
"Skill offered":"வழங்கும் திறன்",
"Skill wanted":"தேவைப்படும் திறன்",
"Offer Skill":"திறனை வழங்கவும்",
"Connect":"இணைக்கவும்",
"Open":"திறந்துள்ளது",
"Requested":"கோரிக்கை அனுப்பப்பட்டது",
"Skill exchange posted successfully.":
"திறன் பரிமாற்ற பதிவு வெற்றிகரமாக சேர்க்கப்பட்டது.",

},

"हिन्दी": {
"Home":"होम",
"Browse":"शिल्प खोजें",
"Product Details":"उत्पाद विवरण",
"Wishlist":"पसंद",
"Cart":"कार्ट",
"Checkout":"चेकआउट",
"Orders":"मेरे ऑर्डर",
"Craft Stories":"शिल्प कहानियाँ",
"Heritage Map":"विरासत मानचित्र",
"AI Image Analyzer":"AI छवि विश्लेषक",
"AI Shopping Assistant":"AI शॉपिंग सहायक",
"Voice Assistant":"वॉइस सहायक",
"Profile":"प्रोफ़ाइल",
"Seller Dashboard":"विक्रेता डैशबोर्ड",
"My Products":"मेरे उत्पाद",
"Add Product":"उत्पाद जोड़ें",
"Seller Orders":"विक्रेता ऑर्डर",
"AI Photo Rescue":"AI फोटो सुधार",
"Waste → Craft AI":"कचरा → शिल्प AI",
"Material Exchange":"सामग्री विनिमय",
"Skill Exchange":"कौशल विनिमय",
"Logout":"लॉगआउट",
"Navigate":"नेविगेशन",
"Quick Login":"त्वरित लॉगिन",
"Register":"पंजीकरण",
"User ID":"यूज़र ID",
"Role":"भूमिका",
"Customer":"ग्राहक",
"Seller / Artisan":"विक्रेता / कारीगर",
"Continue":"जारी रखें",
"Name":"नाम",
"Password":"पासवर्ड",
"Confirm Password":"पासवर्ड की पुष्टि करें",
"Create Account":"खाता बनाएं",
"Discover India Through Its Crafts":"भारत को उसके शिल्पों के माध्यम से जानें",
"Quick Actions":"त्वरित कार्य",
"Shop Crafts":"शिल्प खरीदें",
"AI Shopping":"AI शॉपिंग",
"Tamil Voice Search":"वॉइस खोज",
"My Cart":"मेरी कार्ट",
"My Orders":"मेरे ऑर्डर",
"Open":"खोलें",
"Featured Crafts":"विशेष शिल्प",
"Explore by State":"राज्य के अनुसार खोजें",
"Craft Products":"शिल्प उत्पाद",
"States / Regions":"राज्य / क्षेत्र",
"Craft Traditions":"शिल्प परंपराएँ",
"Artisans":"कारीगर",
"State":"राज्य",
"Craft":"शिल्प",
"Category":"श्रेणी",
"Style":"शैली",
"All":"सभी",
"Traditional":"पारंपरिक",
"Contemporary":"आधुनिक",
"Minimum price":"न्यूनतम कीमत",
"Maximum price":"अधिकतम कीमत",
"Your Cart":"आपकी कार्ट",
"Quantity":"मात्रा",
"Remove":"हटाएं",
"Price Details":"कीमत विवरण",
"Items":"वस्तुएँ",
"Subtotal":"उप-योग",
"Delivery":"डिलीवरी",
"FREE":"मुफ़्त",
"Continue Shopping":"खरीदारी जारी रखें",
"Checkout":"चेकआउट",
"Delivery Address":"डिलीवरी पता",
"Saved addresses":"सहेजे गए पते",
"Full Name":"पूरा नाम",
"Mobile Number":"मोबाइल नंबर",
"City":"शहर",
"State":"राज्य",
"PIN Code":"पिन कोड",
"Order Summary":"ऑर्डर सारांश",
"Offers":"ऑफ़र",
"Payment":"भुगतान",
"Choose payment method":"भुगतान विधि चुनें",
"Place Order":"ऑर्डर करें",
"My Orders":"मेरे ऑर्डर",
"Start Shopping":"खरीदारी शुरू करें",
"Buy these again":"फिर से खरीदें",
"The Story Behind This Craft":"इस शिल्प की कहानी",
"Origin":"उत्पत्ति",
"Customer Reviews":"ग्राहक समीक्षाएँ",
"Submit Review":"समीक्षा भेजें",
"Craft Heritage Map":"भारतीय शिल्प विरासत मानचित्र",
"India Craft Heritage Map":"भारतीय शिल्प विरासत मानचित्र",
"Find Crafts":"शिल्प खोजें",
"Voice language":"वॉइस भाषा",
"Record / Stop":"रिकॉर्ड / रोकें",
"Type your request":"अपना अनुरोध लिखें",
"Search Request":"खोजें",
"Language":"भाषा",
"Save Language":"भाषा सहेजें",
"Revenue":"आय",
"Average Rating":"औसत रेटिंग",
"Stock":"स्टॉक",
"Description":"विवरण",
"Material":"सामग्री",
"Save Product":"उत्पाद सहेजें",
"Update status":"स्थिति अपडेट करें",
"Save status":"स्थिति सहेजें",
"Before":"पहले",
"After":"बाद",
"Leftover material":"बचा हुआ सामान",
"Suggest Craft Ideas":"शिल्प सुझाव दें",
"List Material":"सामग्री सूचीबद्ध करें",
"Browse & Request":"देखें और अनुरोध करें",
"Material offered":"उपलब्ध सामग्री",
"Wanted material":"चाहिए सामग्री",
"Publish":"प्रकाशित करें",
"Send Exchange Request":"विनिमय अनुरोध भेजें",
"Skill Exchange Hub":"कौशल विनिमय केंद्र",
"Skill offered":"उपलब्ध कौशल",
"Skill wanted":"चाहिए कौशल",
"Offer Skill":"कौशल दें",
"Connect":"जुड़ें",
},

"മലയാളം": {
"Home":"ഹോം",
"Browse":"കരകൗശലങ്ങൾ",
"Product Details":"ഉൽപ്പന്ന വിശദാംശങ്ങൾ",
"Wishlist":"ഇഷ്ടങ്ങൾ",
"Cart":"കാർട്ട്",
"Checkout":"ചെക്ക്ഔട്ട്",
"Orders":"എന്റെ ഓർഡറുകൾ",
"Craft Stories":"കരകൗശല കഥകൾ",
"Heritage Map":"പൈതൃക മാപ്പ്",
"AI Image Analyzer":"AI ചിത്രം വിശകലനം",
"AI Shopping Assistant":"AI ഷോപ്പിംഗ് സഹായി",
"Voice Assistant":"വോയ്സ് സഹായി",
"Profile":"പ്രൊഫൈൽ",
"Seller Dashboard":"വിൽപ്പനക്കാരൻ ഡാഷ്ബോർഡ്",
"My Products":"എന്റെ ഉൽപ്പന്നങ്ങൾ",
"Add Product":"ഉൽപ്പന്നം ചേർക്കുക",
"Seller Orders":"വിൽപ്പന ഓർഡറുകൾ",
"AI Photo Rescue":"AI ഫോട്ടോ മെച്ചപ്പെടുത്തൽ",
"Waste → Craft AI":"മാലിന്യം → കരകൗശലം AI",
"Material Exchange":"വസ്തു കൈമാറ്റം",
"Skill Exchange":"കഴിവ് കൈമാറ്റം",
"Logout":"പുറത്ത്",
"Navigate":"നാവിഗേഷൻ",
"Quick Login":"ദ്രുത ലോഗിൻ",
"Register":"രജിസ്റ്റർ",
"User ID":"യൂസർ ID",
"Role":"പങ്ക്",
"Customer":"ഉപഭോക്താവ്",
"Seller / Artisan":"വിൽപ്പനക്കാരൻ / കരകൗശല വിദഗ്ധൻ",
"Continue":"തുടരുക",
"Name":"പേര്",
"Password":"പാസ്‌വേഡ്",
"Confirm Password":"പാസ്‌വേഡ് സ്ഥിരീകരിക്കുക",
"Create Account":"അക്കൗണ്ട് സൃഷ്ടിക്കുക",
"Discover India Through Its Crafts":"കരകൗശലങ്ങളിലൂടെ ഇന്ത്യയെ കണ്ടെത്തൂ",
"Quick Actions":"ദ്രുത പ്രവർത്തനങ്ങൾ",
"Shop Crafts":"കരകൗശലങ്ങൾ വാങ്ങുക",
"AI Shopping":"AI ഷോപ്പിംഗ്",
"My Cart":"എന്റെ കാർട്ട്",
"My Orders":"എന്റെ ഓർഡറുകൾ",
"Open":"തുറക്കുക",
"Featured Crafts":"തിരഞ്ഞെടുത്ത കരകൗശലങ്ങൾ",
"Explore by State":"സംസ്ഥാനമനുസരിച്ച് തിരയുക",
"Craft Products":"കരകൗശല ഉൽപ്പന്നങ്ങൾ",
"States / Regions":"സംസ്ഥാനങ്ങൾ / പ്രദേശങ്ങൾ",
"Craft Traditions":"കരകൗശല പാരമ്പര്യങ്ങൾ",
"Artisans":"കരകൗശല വിദഗ്ധർ",
"State":"സംസ്ഥാനം",
"Craft":"കരകൗശലം",
"Category":"വിഭാഗം",
"Style":"ശൈലി",
"All":"എല്ലാം",
"Traditional":"പരമ്പരാഗതം",
"Contemporary":"ആധുനികം",
"Minimum price":"കുറഞ്ഞ വില",
"Maximum price":"പരമാവധി വില",
"Your Cart":"നിങ്ങളുടെ കാർട്ട്",
"Quantity":"അളവ്",
"Remove":"നീക്കം ചെയ്യുക",
"Price Details":"വില വിശദാംശങ്ങൾ",
"Items":"ഇനങ്ങൾ",
"Subtotal":"ഉപമൊത്തം",
"Delivery":"ഡെലിവറി",
"FREE":"സൗജന്യം",
"Continue Shopping":"ഷോപ്പിംഗ് തുടരുക",
"Checkout":"ചെക്ക്ഔട്ട്",
"Delivery Address":"ഡെലിവറി വിലാസം",
"Saved addresses":"സംരക്ഷിച്ച വിലാസങ്ങൾ",
"Full Name":"പൂർണ്ണ പേര്",
"Mobile Number":"മൊബൈൽ നമ്പർ",
"City":"നഗരം",
"State":"സംസ്ഥാനം",
"PIN Code":"പിൻ കോഡ്",
"Order Summary":"ഓർഡർ സംഗ്രഹം",
"Offers":"ഓഫറുകൾ",
"Payment":"പേയ്മെന്റ്",
"Choose payment method":"പേയ്മെന്റ് രീതി തിരഞ്ഞെടുക്കുക",
"Place Order":"ഓർഡർ ചെയ്യുക",
"The Story Behind This Craft":"ഈ കരകൗശലത്തിന്റെ കഥ",
"Origin":"ഉത്ഭവം",
"Customer Reviews":"ഉപഭോക്തൃ അവലോകനങ്ങൾ",
"Submit Review":"അവലോകനം സമർപ്പിക്കുക",
"Craft Heritage Map":"ഇന്ത്യൻ കരകൗശല പൈതൃക മാപ്പ്",
"India Craft Heritage Map":"ഇന്ത്യൻ കരകൗശല പൈതൃക മാപ്പ്",
"Find Crafts":"കരകൗശലങ്ങൾ കണ്ടെത്തുക",
"Voice language":"വോയ്സ് ഭാഷ",
"Record / Stop":"റെക്കോർഡ് / നിർത്തുക",
"Type your request":"നിങ്ങളുടെ അഭ്യർത്ഥന നൽകുക",
"Search Request":"തിരയുക",
"Language":"ഭാഷ",
"Save Language":"ഭാഷ സംരക്ഷിക്കുക",
"Revenue":"വരുമാനം",
"Average Rating":"ശരാശരി റേറ്റിംഗ്",
"Stock":"സ്റ്റോക്ക്",
"Description":"വിവരണം",
"Material":"വസ്തു",
"Save Product":"ഉൽപ്പന്നം സംരക്ഷിക്കുക",
"Update status":"സ്ഥിതി മാറ്റുക",
"Save status":"സ്ഥിതി സംരക്ഷിക്കുക",
"Before":"മുമ്പ്",
"After":"ശേഷം",
"Leftover material":"ശേഷിച്ച വസ്തു",
"Suggest Craft Ideas":"കരകൗശല ആശയങ്ങൾ നിർദ്ദേശിക്കുക",
"List Material":"വസ്തു ലിസ്റ്റ് ചെയ്യുക",
"Browse & Request":"കാണുക & അഭ്യർത്ഥിക്കുക",
"Material offered":"നൽകുന്ന വസ്തു",
"Wanted material":"ആവശ്യമായ വസ്തു",
"Publish":"പ്രസിദ്ധീകരിക്കുക",
"Send Exchange Request":"കൈമാറ്റ അഭ്യർത്ഥന അയയ്ക്കുക",
"Skill Exchange Hub":"കഴിവ് കൈമാറ്റ കേന്ദ്രം",
"Skill offered":"നൽകുന്ന കഴിവ്",
"Skill wanted":"ആവശ്യമായ കഴിവ്",
"Offer Skill":"കഴിവ് നൽകുക",
"Connect":"ബന്ധപ്പെടുക",
},

"తెలుగు": {
"Home":"హోమ్",
"Browse":"కళలను అన్వేషించండి",
"Product Details":"ఉత్పత్తి వివరాలు",
"Wishlist":"ఇష్టాలు",
"Cart":"కార్ట్",
"Checkout":"చెకౌట్",
"Orders":"నా ఆర్డర్లు",
"Craft Stories":"కళా కథలు",
"Heritage Map":"వారసత్వ మ్యాప్",
"AI Image Analyzer":"AI చిత్రం విశ్లేషణ",
"AI Shopping Assistant":"AI షాపింగ్ సహాయకుడు",
"Voice Assistant":"వాయిస్ సహాయకుడు",
"Profile":"ప్రొఫైల్",
"Seller Dashboard":"విక్రేత డాష్‌బోర్డ్",
"My Products":"నా ఉత్పత్తులు",
"Add Product":"ఉత్పత్తి జోడించండి",
"Seller Orders":"విక్రేత ఆర్డర్లు",
"AI Photo Rescue":"AI ఫోటో మెరుగుదల",
"Waste → Craft AI":"వ్యర్థం → కళ AI",
"Material Exchange":"పదార్థ మార్పిడి",
"Skill Exchange":"నైపుణ్య మార్పిడి",
"Logout":"లాగ్‌అవుట్",
"Navigate":"నావిగేషన్",
"Quick Login":"త్వరిత లాగిన్",
"Register":"రిజిస్టర్",
"User ID":"యూజర్ ID",
"Role":"పాత్ర",
"Customer":"కస్టమర్",
"Seller / Artisan":"విక్రేత / కళాకారుడు",
"Continue":"కొనసాగించండి",
"Name":"పేరు",
"Password":"పాస్‌వర్డ్",
"Confirm Password":"పాస్‌వర్డ్ నిర్ధారించండి",
"Create Account":"ఖాతా సృష్టించండి",
"Discover India Through Its Crafts":"కళల ద్వారా భారతదేశాన్ని తెలుసుకోండి",
"Quick Actions":"త్వరిత చర్యలు",
"Shop Crafts":"కళలను కొనండి",
"AI Shopping":"AI షాపింగ్",
"My Cart":"నా కార్ట్",
"My Orders":"నా ఆర్డర్లు",
"Open":"తెరవండి",
"Featured Crafts":"ఎంచుకున్న కళలు",
"Explore by State":"రాష్ట్రం ప్రకారం చూడండి",
"Craft Products":"కళా ఉత్పత్తులు",
"States / Regions":"రాష్ట్రాలు / ప్రాంతాలు",
"Craft Traditions":"కళా సంప్రదాయాలు",
"Artisans":"కళాకారులు",
"State":"రాష్ట్రం",
"Craft":"కళ",
"Category":"వర్గం",
"Style":"శైలి",
"All":"అన్నీ",
"Traditional":"సాంప్రదాయ",
"Contemporary":"ఆధునిక",
"Minimum price":"కనిష్ట ధర",
"Maximum price":"గరిష్ట ధర",
"Your Cart":"మీ కార్ట్",
"Quantity":"పరిమాణం",
"Remove":"తొలగించు",
"Price Details":"ధర వివరాలు",
"Items":"వస్తువులు",
"Subtotal":"ఉప మొత్తం",
"Delivery":"డెలివరీ",
"FREE":"ఉచితం",
"Continue Shopping":"షాపింగ్ కొనసాగించండి",
"Checkout":"చెకౌట్",
"Delivery Address":"డెలివరీ చిరునామా",
"Saved addresses":"సేవ్ చేసిన చిరునామాలు",
"Full Name":"పూర్తి పేరు",
"Mobile Number":"మొబైల్ నంబర్",
"City":"నగరం",
"State":"రాష్ట్రం",
"PIN Code":"పిన్ కోడ్",
"Order Summary":"ఆర్డర్ సారాంశం",
"Offers":"ఆఫర్లు",
"Payment":"చెల్లింపు",
"Choose payment method":"చెల్లింపు పద్ధతిని ఎంచుకోండి",
"Place Order":"ఆర్డర్ చేయండి",
"The Story Behind This Craft":"ఈ కళ వెనుక కథ",
"Origin":"మూలం",
"Customer Reviews":"కస్టమర్ సమీక్షలు",
"Submit Review":"సమీక్ష పంపండి",
"Craft Heritage Map":"భారతీయ కళా వారసత్వ మ్యాప్",
"India Craft Heritage Map":"భారతీయ కళా వారసత్వ మ్యాప్",
"Find Crafts":"కళలను కనుగొనండి",
"Voice language":"వాయిస్ భాష",
"Record / Stop":"రికార్డ్ / ఆపు",
"Type your request":"మీ అభ్యర్థన టైప్ చేయండి",
"Search Request":"శోధించండి",
"Language":"భాష",
"Save Language":"భాషను సేవ్ చేయండి",
"Revenue":"ఆదాయం",
"Average Rating":"సగటు రేటింగ్",
"Stock":"స్టాక్",
"Description":"వివరణ",
"Material":"పదార్థం",
"Save Product":"ఉత్పత్తిని సేవ్ చేయండి",
"Update status":"స్థితిని మార్చండి",
"Save status":"స్థితిని సేవ్ చేయండి",
"Before":"ముందు",
"After":"తర్వాత",
"Leftover material":"మిగిలిన పదార్థం",
"Suggest Craft Ideas":"కళా ఆలోచనలు సూచించండి",
"List Material":"పదార్థాన్ని జాబితా చేయండి",
"Browse & Request":"చూడండి & అభ్యర్థించండి",
"Material offered":"అందించే పదార్థం",
"Wanted material":"కావలసిన పదార్థం",
"Publish":"ప్రచురించండి",
"Send Exchange Request":"మార్పిడి అభ్యర్థన పంపండి",
"Skill Exchange Hub":"నైపుణ్య మార్పిడి కేంద్రం",
"Skill offered":"అందించే నైపుణ్యం",
"Skill wanted":"కావలసిన నైపుణ్యం",
"Offer Skill":"నైపుణ్యం అందించండి",
"Connect":"కనెక్ట్",
},

"ಕನ್ನಡ": {
"Home":"ಮುಖಪುಟ",
"Browse":"ಕರಕುಶಲ ಅನ್ವೇಷಿಸಿ",
"Product Details":"ಉತ್ಪನ್ನ ವಿವರಗಳು",
"Wishlist":"ಇಷ್ಟಪಟ್ಟವು",
"Cart":"ಕಾರ್ಟ್",
"Checkout":"ಚೆಕ್ಔಟ್",
"Orders":"ನನ್ನ ಆರ್ಡರ್‌ಗಳು",
"Craft Stories":"ಕರಕುಶಲ ಕಥೆಗಳು",
"Heritage Map":"ಪಾರಂಪರಿಕ ನಕ್ಷೆ",
"AI Image Analyzer":"AI ಚಿತ್ರ ವಿಶ್ಲೇಷಣೆ",
"AI Shopping Assistant":"AI ಶಾಪಿಂಗ್ ಸಹಾಯಕ",
"Voice Assistant":"ಧ್ವನಿ ಸಹಾಯಕ",
"Profile":"ಪ್ರೊಫೈಲ್",
"Seller Dashboard":"ಮಾರಾಟಗಾರ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
"My Products":"ನನ್ನ ಉತ್ಪನ್ನಗಳು",
"Add Product":"ಉತ್ಪನ್ನ ಸೇರಿಸಿ",
"Seller Orders":"ಮಾರಾಟಗಾರರ ಆರ್ಡರ್‌ಗಳು",
"AI Photo Rescue":"AI ಫೋಟೋ ಸುಧಾರಣೆ",
"Waste → Craft AI":"ತ್ಯಾಜ್ಯ → ಕರಕುಶಲ AI",
"Material Exchange":"ವಸ್ತು ವಿನಿಮಯ",
"Skill Exchange":"ಕೌಶಲ್ಯ ವಿನಿಮಯ",
"Logout":"ಲಾಗ್‌ಔಟ್",
"Navigate":"ನ್ಯಾವಿಗೇಷನ್",
"Quick Login":"ತ್ವರಿತ ಲಾಗಿನ್",
"Register":"ನೋಂದಣಿ",
"User ID":"ಬಳಕೆದಾರ ID",
"Role":"ಪಾತ್ರ",
"Customer":"ಗ್ರಾಹಕ",
"Seller / Artisan":"ಮಾರಾಟಗಾರ / ಕರಕುಶಲಗಾರ",
"Continue":"ಮುಂದುವರಿಸಿ",
"Name":"ಹೆಸರು",
"Password":"ಪಾಸ್‌ವರ್ಡ್",
"Confirm Password":"ಪಾಸ್‌ವರ್ಡ್ ದೃಢೀಕರಿಸಿ",
"Create Account":"ಖಾತೆ ರಚಿಸಿ",
"Discover India Through Its Crafts":"ಕರಕುಶಲಗಳ ಮೂಲಕ ಭಾರತವನ್ನು ಕಂಡುಕೊಳ್ಳಿ",
"Quick Actions":"ತ್ವರಿತ ಕಾರ್ಯಗಳು",
"Shop Crafts":"ಕರಕುಶಲ ಖರೀದಿಸಿ",
"AI Shopping":"AI ಶಾಪಿಂಗ್",
"My Cart":"ನನ್ನ ಕಾರ್ಟ್",
"My Orders":"ನನ್ನ ಆರ್ಡರ್‌ಗಳು",
"Open":"ತೆರೆಯಿರಿ",
"Featured Crafts":"ವಿಶೇಷ ಕರಕುಶಲಗಳು",
"Explore by State":"ರಾಜ್ಯದ ಮೂಲಕ ಅನ್ವೇಷಿಸಿ",
"Craft Products":"ಕರಕುಶಲ ಉತ್ಪನ್ನಗಳು",
"States / Regions":"ರಾಜ್ಯಗಳು / ಪ್ರದೇಶಗಳು",
"Craft Traditions":"ಕರಕುಶಲ ಪರಂಪರೆಗಳು",
"Artisans":"ಕರಕುಶಲಗಾರರು",
"State":"ರಾಜ್ಯ",
"Craft":"ಕರಕುಶಲ",
"Category":"ವರ್ಗ",
"Style":"ಶೈಲಿ",
"All":"ಎಲ್ಲಾ",
"Traditional":"ಸಾಂಪ್ರದಾಯಿಕ",
"Contemporary":"ಆಧುನಿಕ",
"Minimum price":"ಕನಿಷ್ಠ ಬೆಲೆ",
"Maximum price":"ಗರಿಷ್ಠ ಬೆಲೆ",
"Your Cart":"ನಿಮ್ಮ ಕಾರ್ಟ್",
"Quantity":"ಪ್ರಮಾಣ",
"Remove":"ತೆಗೆದುಹಾಕಿ",
"Price Details":"ಬೆಲೆ ವಿವರಗಳು",
"Items":"ವಸ್ತುಗಳು",
"Subtotal":"ಉಪಮೊತ್ತ",
"Delivery":"ವಿತರಣೆ",
"FREE":"ಉಚಿತ",
"Continue Shopping":"ಶಾಪಿಂಗ್ ಮುಂದುವರಿಸಿ",
"Checkout":"ಚೆಕ್ಔಟ್",
"Delivery Address":"ವಿತರಣಾ ವಿಳಾಸ",
"Saved addresses":"ಉಳಿಸಿದ ವಿಳಾಸಗಳು",
"Full Name":"ಪೂರ್ಣ ಹೆಸರು",
"Mobile Number":"ಮೊಬೈಲ್ ಸಂಖ್ಯೆ",
"City":"ನಗರ",
"State":"ರಾಜ್ಯ",
"PIN Code":"PIN ಕೋಡ್",
"Order Summary":"ಆರ್ಡರ್ ಸಾರಾಂಶ",
"Offers":"ಆಫರ್‌ಗಳು",
"Payment":"ಪಾವತಿ",
"Choose payment method":"ಪಾವತಿ ವಿಧಾನ ಆಯ್ಕೆಮಾಡಿ",
"Place Order":"ಆರ್ಡರ್ ಮಾಡಿ",
"The Story Behind This Craft":"ಈ ಕರಕುಶಲದ ಹಿಂದಿನ ಕಥೆ",
"Origin":"ಮೂಲ",
"Customer Reviews":"ಗ್ರಾಹಕರ ವಿಮರ್ಶೆಗಳು",
"Submit Review":"ವಿಮರ್ಶೆ ಸಲ್ಲಿಸಿ",
"Craft Heritage Map":"ಭಾರತೀಯ ಕರಕುಶಲ ಪಾರಂಪರಿಕ ನಕ್ಷೆ",
"India Craft Heritage Map":"ಭಾರತೀಯ ಕರಕುಶಲ ಪಾರಂಪರಿಕ ನಕ್ಷೆ",
"Find Crafts":"ಕರಕುಶಲ ಹುಡುಕಿ",
"Voice language":"ಧ್ವನಿ ಭಾಷೆ",
"Record / Stop":"ರೆಕಾರ್ಡ್ / ನಿಲ್ಲಿಸಿ",
"Type your request":"ನಿಮ್ಮ ವಿನಂತಿ ಟೈಪ್ ಮಾಡಿ",
"Search Request":"ಹುಡುಕಿ",
"Language":"ಭಾಷೆ",
"Save Language":"ಭಾಷೆ ಉಳಿಸಿ",
"Revenue":"ಆದಾಯ",
"Average Rating":"ಸರಾಸರಿ ರೇಟಿಂಗ್",
"Stock":"ಸ್ಟಾಕ್",
"Description":"ವಿವರಣೆ",
"Material":"ವಸ್ತು",
"Save Product":"ಉತ್ಪನ್ನ ಉಳಿಸಿ",
"Update status":"ಸ್ಥಿತಿ ಬದಲಿಸಿ",
"Save status":"ಸ್ಥಿತಿ ಉಳಿಸಿ",
"Before":"ಮೊದಲು",
"After":"ನಂತರ",
"Leftover material":"ಉಳಿದ ವಸ್ತು",
"Suggest Craft Ideas":"ಕರಕುಶಲ ಸಲಹೆ ನೀಡಿ",
"List Material":"ವಸ್ತು ಪಟ್ಟಿ ಮಾಡಿ",
"Browse & Request":"ನೋಡಿ ಮತ್ತು ವಿನಂತಿಸಿ",
"Material offered":"ನೀಡುವ ವಸ್ತು",
"Wanted material":"ಬೇಕಾದ ವಸ್ತು",
"Publish":"ಪ್ರಕಟಿಸಿ",
"Send Exchange Request":"ವಿನಿಮಯ ವಿನಂತಿ ಕಳುಹಿಸಿ",
"Skill Exchange Hub":"ಕೌಶಲ್ಯ ವಿನಿಮಯ ಕೇಂದ್ರ",
"Skill offered":"ನೀಡುವ ಕೌಶಲ್ಯ",
"Skill wanted":"ಬೇಕಾದ ಕೌಶಲ್ಯ",
"Offer Skill":"ಕೌಶಲ್ಯ ನೀಡಿ",
"Connect":"ಸಂಪರ್ಕಿಸಿ",
}

}


def current_lang():
    return st.session_state.get("language", "English")


def T(text):
    lang = current_lang()
    return TRANSLATIONS.get(lang, {}).get(text, text)


# ============================================================
# AI
# ============================================================

def ai_client():
    if Groq is None:
        return None

    try:
        key = st.secrets.get("GROQ_API_KEY")

        if key and key != "YOUR_API_KEY_HERE":
            return Groq(api_key=key)

    except Exception:
        pass

    return None


def gemini_generate(prompt, image_bytes=None, mime_type="image/jpeg"):
    """Reliable Gemini text/vision call used by both customer and seller image AI."""
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if not api_key or api_key == "YOUR_API_KEY_HERE":
            return ""

        parts = []
        if image_bytes:
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": base64.b64encode(image_bytes).decode("utf-8")
                }
            })
        parts.append({"text": prompt})

        # Keep Gemini as the primary image provider because this path is
        # independent of the Groq vision model and uses the configured Gemini key.
        for model in ("gemini-3.8-flash", "gemini-3.7-flash"):
            try:
                response = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    headers={
                        "x-goog-api-key": api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "contents": [{"role": "user", "parts": parts}]
                    },
                    timeout=45
                )
                if not response.ok:
                    continue
                payload = response.json()
                for candidate in payload.get("candidates") or []:
                    content = candidate.get("content") or {}
                    output_parts = content.get("parts") or []
                    text = "".join(str(part.get("text", "")) for part in output_parts).strip()
                    if text:
                        return text
            except Exception:
                continue
    except Exception:
        pass
    return ""


def ai_call(prompt):
    client = ai_client()

    if not client:
        return None

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content":
                    "You are KAIVANNAM, an Indian handicraft marketplace assistant. "
                    "Be concise. Never invent catalog products. "
                    "Answer in the user's requested language."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=700
        )

        return response.choices[0].message.content

    except Exception:
        return None



def groq_vision_generate(prompt, image_bytes, mime_type="image/jpeg"):
    """Groq vision backup. Returns empty text on provider failure."""
    client = ai_client()
    if not client or not image_bytes:
        return ""
    try:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are KAIVANNAM's visual product analyst. Analyze ONLY the exact image supplied. "
                        "Describe visible facts and do not invent unsupported details."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}}
                    ]
                }
            ],
            temperature=0.1,
            max_completion_tokens=900,
            stream=False
        )
        return (response.choices[0].message.content or "").strip()
    except Exception:
        return ""


def ai_product_pricing_and_description(name, craft, category, state, district, material, image_path, fallback_price, fallback_description):
    """Generate complete seller listing metadata using Gemini and the existing live marketplace references."""
    fallback = (fallback_price, fallback_description, name, craft, category, state, district, material)

    live_market_lines = []
    try:
        search_terms = [
            f"{name} {craft} {material} India handmade price",
            f"{craft} {category} {state} handmade India price",
            f"{name} artisan handmade India price"
        ]
        domains = [
            "amazon.in", "etsy.com", "indiahandmade.com",
            "flipkart.com", "myntra.com", "craftsvilla.com"
        ]
        for term in search_terms:
            query = term + " " + " OR ".join("site:" + d for d in domains)
            url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                page = resp.read().decode("utf-8", errors="ignore")
            page_text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.S | re.I)
            page_text = re.sub(r"<[^>]+>", " ", page_text)
            page_text = html_lib.unescape(re.sub(r"\s+", " ", page_text)).strip()
            for m in re.finditer(r"(.{0,220}(?:₹|Rs\.?|INR)\s?[0-9][0-9,]*(?:\.\d{1,2})?.{0,220})", page_text, re.I):
                snippet = m.group(1).strip()
                if snippet and snippet not in live_market_lines:
                    live_market_lines.append(snippet)
                if len(live_market_lines) >= 18:
                    break
            if len(live_market_lines) >= 18:
                break
    except Exception:
        live_market_lines = []

    market_reference = "\n".join(live_market_lines) if live_market_lines else (
        "No live external marketplace references were available. Use the product attributes for a conservative estimate."
    )

    image_bytes = None
    mime = "image/jpeg"
    if image_path:
        try:
            full_path = APP_DIR / image_path
            if full_path.exists():
                image_bytes = full_path.read_bytes()
                suffix = full_path.suffix.lower()
                mime = "image/png" if suffix == ".png" else "image/webp" if suffix == ".webp" else "image/jpeg"
        except Exception:
            pass

    prompt = (
        "Create complete metadata for ONE artisan product listing. The uploaded image is the primary source for identifying the product. "
        "If Product name, Craft type, Category, State, District/Region, or Material are blank, infer them from visible evidence in the image when reasonably possible. "
        "Do not invent unsupported location or material details; use an empty string when it cannot be identified. "
        "Choose Category only from: Painting, Textiles, Pottery, Wood Craft, Metal Craft, Jewellery, Bamboo & Cane, Embroidery, Home Decor, Toys, Eco-friendly Crafts, Stone Craft, Leather Craft. "
        "Write a clear factual marketplace description. For price, analyze CURRENT EXTERNAL ONLINE MARKETPLACE LISTINGS below; compare multiple listings when available and recommend a practical INR selling price that can be lower than comparable listings when the references support it. "
        "Output ONLY valid JSON with exactly these keys: product_name, craft_type, category, state, district, material, recommended_price, description.\n\n"
        f"Product name: {name or 'BLANK'}\nCraft type: {craft or 'BLANK'}\nCategory: {category or 'BLANK'}\n"
        f"State: {state or 'BLANK'}\nDistrict/Region: {district or 'BLANK'}\nMaterial: {material or 'BLANK'}\n\n"
        "CURRENT EXTERNAL MARKETPLACE REFERENCES:\n" + market_reference
    )

    raw = gemini_generate(prompt, image_bytes=image_bytes, mime_type=mime)
    try:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return fallback
        data = __import__("json").loads(match.group(0))
        recommended = int(round(float(data.get("recommended_price", fallback_price))))
        recommended = max(1, min(100000, recommended))
        description = str(data.get("description", "")).strip() or fallback_description
        product_name = str(data.get("product_name", "")).strip() or name
        craft_type = str(data.get("craft_type", "")).strip() or craft
        allowed = ["Painting", "Textiles", "Pottery", "Wood Craft", "Metal Craft", "Jewellery", "Bamboo & Cane", "Embroidery", "Home Decor", "Toys", "Eco-friendly Crafts", "Stone Craft", "Leather Craft"]
        ai_category = str(data.get("category", "")).strip()
        ai_category = next((x for x in allowed if x.lower() == ai_category.lower()), category)
        ai_state = str(data.get("state", "")).strip() or state
        ai_district = str(data.get("district", "")).strip() or district
        ai_material = str(data.get("material", "")).strip() or material
        return recommended, description, product_name, craft_type, ai_category, ai_state, ai_district, ai_material
    except Exception:
        return fallback


def ai_product_image_price_and_description(image_path, name="", craft="", category="", state="", district="", material="", fallback_price=500.0, fallback_description=""):
    """Generate description and price from the uploaded product image."""
    client = ai_client()
    if not client or not image_path:
        return float(fallback_price), fallback_description

    try:
        full_path = APP_DIR / image_path
        if not full_path.exists():
            return float(fallback_price), fallback_description

        # Normalize mobile-camera photos before sending them to the vision model.
        # This fixes the common EXIF rotation used by phone cameras while keeping
        # the original uploaded file untouched for the final product image.
        image_bytes = full_path.read_bytes()
        suffix = full_path.suffix.lower()
        mime = (
            "image/png" if suffix == ".png"
            else "image/webp" if suffix == ".webp"
            else "image/jpeg"
        )
        if suffix in {".jpg", ".jpeg"}:
            try:
                from PIL import Image, ImageOps
                from io import BytesIO
                image = Image.open(BytesIO(image_bytes))
                image = ImageOps.exif_transpose(image).convert("RGB")
                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=92)
                image_bytes = buffer.getvalue()
            except Exception:
                pass
        encoded = base64.b64encode(image_bytes).decode("utf-8")

        description_language = {
            "English": "English",
            "தமிழ்": "Tamil (தமிழ்)",
            "हिन्दी": "Hindi (हिन्दी)",
            "മലയാളം": "Malayalam (മലയാളം)",
            "తెలుగు": "Telugu (తెలుగు)",
            "ಕನ್ನಡ": "Kannada (ಕನ್ನಡ)"
        }.get(current_lang(), "English")

        # Fetch fresh public marketplace prices so the AI price is grounded in
        # current comparable listings instead of being based only on an estimate.
        market_lines = []
        market_prices = []
        try:
            base_terms = [x for x in [name, craft, material, category, state] if x and str(x).strip()]
            search_base = " ".join(str(x).strip() for x in base_terms[:5]) + " handmade India price"
            marketplace_queries = [
                search_base + " site:amazon.in",
                search_base + " site:flipkart.com",
                search_base + " site:etsy.com",
                search_base + " site:indiahandmade.com",
            ]
            for query in marketplace_queries:
                url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent":
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 Chrome/153 Safari/537.36"
                    }
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    page = resp.read().decode("utf-8", errors="ignore")
                page_text = re.sub(
                    r"<script.*?</script>|<style.*?</style>",
                    " ",
                    page,
                    flags=re.S | re.I
                )
                page_text = re.sub(r"<[^>]+>", " ", page_text)
                page_text = html_lib.unescape(re.sub(r"\s+", " ", page_text)).strip()

                # Keep marketplace snippets and extract only plausible INR prices.
                for match in re.finditer(
                    r"(.{0,180}(?:₹|Rs\.?|INR)\s?([0-9][0-9,]*(?:\.[0-9]{1,2})?).{0,180})",
                    page_text,
                    re.I
                ):
                    snippet = match.group(1).strip()
                    try:
                        value = float(match.group(2).replace(",", ""))
                    except Exception:
                        continue
                    if 50 <= value <= 100000:
                        market_prices.append(value)
                        if snippet not in market_lines:
                            market_lines.append(snippet)
                    if len(market_lines) >= 20:
                        break
                if len(market_lines) >= 20:
                    break
        except Exception:
            pass

        # Use the median of fresh comparable listings as a stable market anchor.
        market_anchor = None
        if market_prices:
            ordered_prices = sorted(market_prices)
            mid = len(ordered_prices) // 2
            market_anchor = (
                ordered_prices[mid]
                if len(ordered_prices) % 2
                else (ordered_prices[mid - 1] + ordered_prices[mid]) / 2
            )

        market_reference = "\n".join(market_lines) if market_lines else "No current marketplace price references were retrieved."
        anchor_text = (
            f"Fresh marketplace price median: ₹{market_anchor:,.0f}."
            if market_anchor is not None
            else "No reliable marketplace median was available."
        )

        prompt = (
            "Analyze the uploaded artisan product image. Return ONLY valid JSON with exactly two keys: "
            "description and recommended_price. "
            "Write the description ONLY in English. This English description is the canonical product description "
            "and will be translated separately into the dashboard-selected language. "
            "The description must be a clear marketplace description based on what is visibly shown: "
            "appearance, shape, colors, visible design, and material/technique only when identifiable. "
            "Do not invent location, artisan identity, history, or unsupported facts. "
            "For recommended_price, use the CURRENT marketplace references below as a benchmark, but make the final price "
            "affordable for low-income/marginal customers while still giving the artisan a fair return for materials, skill, "
            "time and craftsmanship. For comparable products, target roughly 75-90% of the reliable marketplace median rather "
            "than premium marketplace pricing. Do not underprice skilled handmade work or choose an unrealistically cheap price. "
            "If the marketplace references are noisy or unavailable, estimate a fair affordable Indian artisan price from the "
            "visible size, materials, complexity and craftsmanship. Prefer practical rounded prices such as 199, 249, 299, 349, "
            "399, 449, 499, 599, 699, 799, 899, 999, 1199, 1499, etc., as appropriate. "
            "The suggested price must balance customer affordability and artisan earnings; it is a recommendation and the seller "
            "can edit it before saving. Use a whole number between 100 and 50000. "
            f"Seller product name: {name or 'blank'}; craft type: {craft or 'blank'}; category: {category or 'blank'}; "
            f"state: {state or 'blank'}; district: {district or 'blank'}; material: {material or 'blank'}.\n\n"
            f"{anchor_text}\n"
            "CURRENT MARKETPLACE REFERENCES:\n" + market_reference
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are KAIVANNAM's product listing assistant. Return only valid JSON. "
                    "The description MUST be written only in English. Do not translate it here; "
                    "the English description will be translated separately after image analysis."
                )
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{encoded}"
                        }
                    }
                ]
            }
        ]

        raw = ""
        for model in [
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "qwen/qwen3.8-27b"
        ]:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.1,
                    max_completion_tokens=500
                )
                raw = (response.choices[0].message.content or "").strip()
                if raw:
                    break
            except Exception:
                continue
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return float(fallback_price), fallback_description

        data = __import__("json").loads(match.group(0))
        english_description = str(data.get("description", "")).strip() or fallback_description
        description = english_description

        # Generate the product description in English first, then translate that
        # canonical description into the dashboard-selected language. This keeps
        # the image analysis consistent while allowing the seller to switch
        # languages without changing the product facts.
        if english_description and current_lang() != "English":
            translation_language = {
                "தமிழ்": "Tamil (தமிழ்)",
                "हिन्दी": "Hindi (हिन्दी)",
                "മലയാളം": "Malayalam (മലയാളം)",
                "తెలుగు": "Telugu (తెలుగు)",
                "ಕನ್ನಡ": "Kannada (ಕನ್ನಡ)"
            }.get(current_lang(), current_lang())
            try:
                translation_response = client.chat.completions.create(
                    model="qwen/qwen3.8-27b",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are KAIVANNAM's product-description translator. "
                                f"Translate the English product description into {translation_language}. "
                                "Preserve the exact product facts and meaning. Do not add, remove, or invent details. "
                                "Return only the translated description, with no labels or explanation."
                            )
                        },
                        {
                            "role": "user",
                            "content": english_description
                        }
                    ],
                    temperature=0.1,
                    max_completion_tokens=500
                )
                translated = (translation_response.choices[0].message.content or "").strip()
                if translated:
                    description = translated
                else:
                    raise ValueError("Empty translation")
            except Exception:
                fallback_translation = ai_call(
                    "Translate the following product description into "
                    f"{translation_language}. Preserve every product fact and detail exactly. "
                    "Do not add, remove, summarize, or explain anything. Return only the translated description.\n\n"
                    + english_description
                )
                if fallback_translation and fallback_translation.strip():
                    description = fallback_translation.strip()
                else:
                    description = english_description

        try:
            ai_price = float(data.get("recommended_price", fallback_price))
        except Exception:
            ai_price = float(fallback_price)

        # Keep the description logic from the earlier working version.
        # For price, make KAIVANNAM moderately cheaper than comparable
        # marketplace listings when a reliable market median is available.
        if market_anchor is not None:
            recommended_price = int(round((market_anchor * 0.80) / 10.0) * 10)
            # Do not let the AI push the price back up above the competitive
            # marketplace target. The seller can still edit it before saving.
            recommended_price = min(recommended_price, int(round(ai_price)))
        else:
            recommended_price = int(round(ai_price))

        recommended_price = max(100, min(50000, recommended_price))
        return float(recommended_price), description
    except Exception:
        return float(fallback_price), fallback_description


def ai_mode():
    if ai_client():
        return "🟢 Live AI"
    return "🟡 AI Demo Mode – Add GROQ_API_KEY to enable live AI"


# ============================================================
# IMAGE
# ============================================================

def product_image(r):

    r = dict(r)

    # Always prefer the exact image uploaded/saved with this product.
    # Never replace a valid uploaded product image with a category/demo image.
    image_path = r.get("image_path")
    if image_path:
        p = Path(str(image_path))
        if not p.is_absolute():
            p = APP_DIR / p
        if p.exists() and p.is_file():
            return p

    craft = r.get("craft_type", "")

    if craft in REAL_IMAGE_URLS:
        return REAL_IMAGE_URLS[craft]

    category = r.get("category", "")

    if category in REAL_CATEGORY_URLS:
        return REAL_CATEGORY_URLS[category]

    return REAL_IMAGE_URLS["Madhubani Painting"]


def data_url(path):

    if isinstance(path, str) and path.startswith(
        ("http://", "https://")
    ):
        return path

    try:
        path = Path(path)
        ext = path.suffix.lower().replace(".", "")

        mime = "jpeg" if ext in ("jpg", "jpeg") else ext

        return (
            f"data:image/{mime};base64,"
            + base64.b64encode(path.read_bytes()).decode()
        )

    except Exception:
        return ""


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():

    con = db()

    con.executescript("""

    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        name TEXT,
        phone TEXT,
        address TEXT,
        language TEXT DEFAULT 'English',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS artisans(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE,
        craft TEXT,
        state TEXT,
        district TEXT,
        village TEXT,
        experience INTEGER DEFAULT 5,
        bio TEXT,
        skills TEXT
    );

    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        craft_type TEXT,
        category TEXT,
        state TEXT,
        district TEXT,
        region TEXT,
        material TEXT,
        description TEXT,
        price REAL,
        stock INTEGER,
        artisan TEXT,
        artisan_user_id TEXT,
        rating REAL DEFAULT 0,
        review_count INTEGER DEFAULT 0,
        style TEXT,
        image_key TEXT,
        image_path TEXT,
        cultural_significance TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS cart(
        user_id TEXT,
        product_id INTEGER,
        quantity INTEGER,
        PRIMARY KEY(user_id,product_id)
    );

    CREATE TABLE IF NOT EXISTS wishlist(
        user_id TEXT,
        product_id INTEGER,
        PRIMARY KEY(user_id,product_id)
    );

    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        total REAL,
        status TEXT DEFAULT 'Order Placed',
        payment_method TEXT,
        payment_status TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS order_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        price REAL
    );

    CREATE TABLE IF NOT EXISTS payments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        method TEXT,
        status TEXT,
        amount REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS delivery_tracking(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        status TEXT,
        event_time TEXT
    );

    CREATE TABLE IF NOT EXISTS reviews(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        product_id INTEGER,
        rating INTEGER,
        review TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS craft_stories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artisan TEXT,
        craft TEXT,
        city TEXT,
        state TEXT,
        experience INTEGER,
        story TEXT,
        image_key TEXT
    );

    CREATE TABLE IF NOT EXISTS barter_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user TEXT,
        to_user TEXT,
        material TEXT,
        offer TEXT,
        status TEXT DEFAULT 'Pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS material_listings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        material TEXT,
        quantity TEXT,
        location TEXT,
        wanted TEXT,
        description TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS skill_exchange(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user TEXT,
        skill TEXT,
        wanted_skill TEXT,
        status TEXT DEFAULT 'Open',
        to_user TEXT
    );

    CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        message TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS shipping_addresses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        line1 TEXT NOT NULL,
        line2 TEXT,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        pincode TEXT NOT NULL,
        landmark TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS return_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        order_item_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        reason TEXT NOT NULL,
        status TEXT DEFAULT 'Requested',
        refund_status TEXT DEFAULT 'Pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    """)

    # Existing DB migration
    # Keep older databases compatible with the current users table.
    for col, typ in [
        ("name", "TEXT"),
        ("phone", "TEXT"),
        ("address", "TEXT"),
        ("language", "TEXT DEFAULT 'English'"),
    ]:
        try:
            con.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError:
            pass

    for col, typ in [
        ("shipping_name", "TEXT"),
        ("shipping_phone", "TEXT"),
        ("shipping_address", "TEXT"),
        ("shipping_city", "TEXT"),
        ("shipping_state", "TEXT"),
        ("shipping_pincode", "TEXT"),
        ("shipping_landmark", "TEXT"),
        ("subtotal", "REAL"),
        ("delivery_charge", "REAL"),
        ("discount", "REAL"),
        ("coupon_code", "TEXT")
    ]:

        try:
            con.execute(
                f"ALTER TABLE orders ADD COLUMN {col} {typ}"
            )
        except sqlite3.OperationalError:
            pass

    # Demo accounts
    for uid, role, name in [
        ("customer01", "Customer", "Demo Customer"),
        ("artisan01", "Seller", "Lakshmi Artisan")
    ]:

        con.execute(
            """
            INSERT OR IGNORE INTO users
            (user_id,password_hash,role,name)
            VALUES(?,?,?,?)
            """,
            (
                uid,
                hash_pw("demo123"),
                role,
                name
            )
        )

    con.execute(
        """
        INSERT OR IGNORE INTO artisans
        (user_id,craft,state,district,experience,bio,skills)
        VALUES(?,?,?,?,?,?,?)
        """,
        (
            "artisan01",
            "Thanjavur Painting",
            "Tamil Nadu",
            "Thanjavur",
            30,
            "Preserving traditional painting skills for a new generation.",
            "Painting,Gold Leaf,Storytelling"
        )
    )

    seed_products(con)
    seed_stories(con)
    seed_demo_orders(con)

    con.commit()
    con.close()


def seed_products(con):

    count = con.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    if count >= 100:
        return

    con.execute("DELETE FROM products")

    rows = []

    for i, (
        craft,
        state,
        district,
        category,
        material
    ) in enumerate(CRAFTS):

        for v in range(2):

            artisan = ARTISANS[i % len(ARTISANS)]

            name = (
                f"{VARIANTS[(i+v) % len(VARIANTS)]} – {craft}"
            )

            price = 650 + (
                (i * 173 + v * 311) % 6800
            )

            rating = round(
                4.1 + ((i + v) % 9) / 10,
                1
            )

            style = (
                "Traditional"
                if (i + v) % 4
                else "Contemporary"
            )

            rows.append(
                (
                    name,
                    craft,
                    category,
                    state,
                    district,
                    f"{district} region",
                    material,
                    f"Handcrafted {craft} from {district}, created using traditional techniques and artisan skill.",
                    price,
                    5 + (i * 3) % 40,
                    artisan,
                    "artisan01",
                    rating,
                    8 + (i * 7) % 74,
                    style,
                    keyify(craft),
                    "",
                    f"A regional {craft} tradition associated with the living craft heritage of {state}."
                )
            )

    con.executemany(
        """
        INSERT INTO products(
            name,craft_type,category,state,district,region,
            material,description,price,stock,artisan,
            artisan_user_id,rating,review_count,style,
            image_key,image_path,cultural_significance
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        rows
    )


def seed_stories(con):

    if con.execute(
        "SELECT COUNT(*) FROM craft_stories"
    ).fetchone()[0]:
        return

    rows = [
        (
            "Lakshmi",
            "Thanjavur Painting",
            "Thanjavur",
            "Tamil Nadu",
            30,
            "Layered colours, patient gold work and family-taught techniques keep this tradition alive.",
            "thanjavur_painting"
        ),
        (
            "Sreedevi",
            "Aranmula Mirror",
            "Aranmula",
            "Kerala",
            24,
            "A specialised metal craft whose finishing knowledge is passed through generations.",
            "aranmula_mirror"
        ),
        (
            "Arun",
            "Blue Pottery",
            "Jaipur",
            "Rajasthan",
            18,
            "Traditional blue pottery forms are adapted for contemporary homes while retaining their identity.",
            "blue_pottery"
        ),
        (
            "Maya",
            "Pattachitra",
            "Puri",
            "Odisha",
            26,
            "Natural pigments and fine line work are used to narrate traditional stories on cloth.",
            "pattachitra"
        )
    ]

    con.executemany(
        """
        INSERT INTO craft_stories
        (artisan,craft,city,state,experience,story,image_key)
        VALUES(?,?,?,?,?,?,?)
        """,
        rows
    )


def seed_demo_orders(con):

    if con.execute(
        "SELECT COUNT(*) FROM orders"
    ).fetchone()[0]:
        return

    products = con.execute(
        "SELECT id,price FROM products ORDER BY id LIMIT 2"
    ).fetchall()

    if len(products) < 2:
        return

    total = products[0][1] + products[1][1]

    cur = con.execute(
        """
        INSERT INTO orders
        (user_id,total,status,payment_method,payment_status)
        VALUES(?,?,?,?,?)
        """,
        (
            "customer01",
            total,
            "Delivered",
            "UPI",
            "Demo Payment"
        )
    )

    order_id = cur.lastrowid

    for product in products:

        con.execute(
            """
            INSERT INTO order_items
            (order_id,product_id,quantity,price)
            VALUES(?,?,?,?)
            """,
            (
                order_id,
                product[0],
                1,
                product[1]
            )
        )

    for status in STATUSES:

        con.execute(
            """
            INSERT INTO delivery_tracking
            (order_id,status,event_time)
            VALUES(?,?,?)
            """,
            (
                order_id,
                status,
                datetime.now().isoformat()
            )
        )

    con.execute(
        """
        INSERT INTO payments
        (order_id,method,status,amount)
        VALUES(?,?,?,?)
        """,
        (
            order_id,
            "UPI",
            "Demo Payment",
            total
        )
    )


init_db()


# ============================================================
# USER HELPERS
# ============================================================

def current_user():
    return st.session_state.get("user")


def restore_saved_login():
    """Restore the last logged-in account when the browser session is reopened."""
    if st.session_state.get("user"):
        return True

    try:
        saved_user_id = st.query_params.get("user_id")
    except Exception:
        saved_user_id = None

    if not saved_user_id:
        return False

    user = one(
        "SELECT * FROM users WHERE user_id=?",
        (str(saved_user_id).strip(),)
    )

    if not user:
        try:
            st.query_params.clear()
        except Exception:
            pass
        return False

    st.session_state.user = dictrow(user)
    st.session_state.language = (
        user["language"]
        if user["language"] in LANGS
        else "English"
    )
    st.session_state.page = (
        "Seller Dashboard"
        if user["role"] == "Seller"
        else "Home"
    )
    return True


def add_cart(product_id, quantity=1):

    exec_sql(
        """
        INSERT INTO cart(user_id,product_id,quantity)
        VALUES(?,?,?)
        ON CONFLICT(user_id,product_id)
        DO UPDATE SET quantity=quantity+excluded.quantity
        """,
        (
            current_user()["user_id"],
            product_id,
            quantity
        )
    )


def add_wishlist(product_id):

    exec_sql(
        """
        INSERT OR IGNORE INTO wishlist
        (user_id,product_id)
        VALUES(?,?)
        """,
        (
            current_user()["user_id"],
            product_id
        )
    )


def remove_wishlist(product_id):

    exec_sql(
        """
        DELETE FROM wishlist
        WHERE user_id=? AND product_id=?
        """,
        (
            current_user()["user_id"],
            product_id
        )
    )


def get_cart():

    return q(
        """
        SELECT p.*,c.quantity
        FROM cart c
        JOIN products p ON p.id=c.product_id
        WHERE c.user_id=?
        ORDER BY c.rowid DESC
        """,
        (
            current_user()["user_id"],
        )
    )


# ============================================================
# PRODUCT CARD
# ============================================================

def product_card(r, prefix="p"):

    r = dictrow(r)

    path = product_image(r)

    url = data_url(path)

    # Render the card with native Streamlit elements instead of raw HTML.
    # This guarantees that <div>, </div>, and class names can never appear
    # as literal text, even on older Streamlit versions.
    with st.container():
        if url:
            st.image(url, use_container_width=True)

        st.markdown(
            f"**{r['name']}**"
        )

        st.caption(
            f"{r['craft_type']} • {r['state']} • {r['district']}"
        )

        st.caption(
            f"{T('Artisans')}: {r['artisan']} • {r['material']}"
        )

        st.write(
            f"⭐ {r['rating']:.1f} ({r['review_count']})"
        )

        st.markdown(
            f"### ₹{r['price']:,.0f}"
        )

    a, b, c, d = st.columns(4)

    if a.button(
        "🛒",
        key=f"cart_{prefix}_{r['id']}",
        help="Add to Cart"
    ):
        add_cart(r["id"])
        st.toast("Added to cart")

    wish_exists = one(
        "SELECT 1 FROM wishlist WHERE user_id=? AND product_id=?",
        (current_user()["user_id"], r["id"])
    ) is not None

    if b.button(
        "❤️" if wish_exists else "♡",
        key=f"wish_{prefix}_{r['id']}",
        help="Wishlist"
    ):
        if wish_exists:
            remove_wishlist(r["id"])
        else:
            add_wishlist(r["id"])
        st.rerun()

    if c.button(
        T("Product Details"),
        key=f"view_{prefix}_{r['id']}"
    ):
        st.session_state.detail_id = r["id"]
        st.session_state.page = "Product Details"
        st.rerun()

    if d.button(
        "Buy",
        key=f"buy_{prefix}_{r['id']}"
    ):
        add_cart(r["id"])
        st.session_state.page = "Checkout"
        st.rerun()


# ============================================================
# LOGIN
# ============================================================

def login_page():

    logos = [
        p for p in LOGO_DIR.glob("*")
        if p.suffix.lower() in (".png", ".jpg", ".jpeg")
    ]

    st.markdown(
        """
        <div class="hero">
            <h1>கைவண்ணம் • KAIVANNAM</h1>
            <p>
            கைவினைக் கலைஞர்களின் கைவண்ணம்
            நம்ம ஆதரவில் மலரட்டும்
            </p>
            <p>
            Indian Artisan Marketplace
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if logos:
        st.image(str(logos[0]), width=170)

    # Language before login
    language = st.selectbox(
        "🌐 Language / மொழி",
        LANGS,
        index=LANGS.index(
            st.session_state.get("language", "English")
        )
    )

    if language != st.session_state.get("language"):
        st.session_state.language = language
        st.rerun()

    t1, t2 = st.tabs([
        T("Quick Login"),
        T("Register")
    ])

    with t1:

        uid = st.text_input(
            T("User ID"),
            placeholder="customer01 / artisan01"
        )

        role = st.selectbox(
            T("Role"),
            [
                T("Customer"),
                T("Seller / Artisan")
            ]
        )

        if st.button(
            T("Continue"),
            type="primary"
        ):

            wanted = (
                "Seller"
                if "Seller" in role
                or "விற்பனையாளர்" in role
                or "विक्रेता" in role
                else "Customer"
            )

            user = one(
                "SELECT * FROM users WHERE user_id=?",
                (uid.strip(),)
            )

            if user and user["role"] == wanted:

                st.session_state.user = dictrow(user)

                # Remember this login in the browser URL so reopening the app
                # does not require entering the same User ID again.
                try:
                    st.query_params["user_id"] = user["user_id"]
                except Exception:
                    pass

                st.session_state.language = (
                    user["language"]
                    if user["language"] in LANGS
                    else "English"
                )

                st.session_state.page = (
                    "Seller Dashboard"
                    if wanted == "Seller"
                    else "Home"
                )

                st.rerun()

            else:
                st.error(
                    "Account not found for selected role."
                )

        st.caption(
            "Demo: customer01 / artisan01"
        )

    with t2:

        uid = st.text_input(
            T("User ID"),
            key="reg_uid"
        )

        name = st.text_input(
            T("Name"),
            key="reg_name"
        )

        phone = st.text_input(
            "Phone Number",
            key="reg_phone",
            placeholder="10-digit mobile number"
        )

        address = st.text_area(
            "Address",
            key="reg_address",
            placeholder="House / Street / Area / City / State / PIN"
        )

        role = st.selectbox(
            T("Role"),
            ["Customer", "Seller"],
            key="reg_role"
        )

        pw = st.text_input(
            T("Password"),
            type="password",
            key="reg_pw"
        )

        cpw = st.text_input(
            T("Confirm Password"),
            type="password",
            key="reg_cpw"
        )

        if st.button(
            T("Create Account")
        ):

            if not uid.strip() or not name.strip() or not phone.strip() or not address.strip() or not pw:

                st.error("Please complete all required fields.")

            elif not re.fullmatch(r"[0-9]{10}", re.sub(r"\D", "", phone)):

                st.error("Enter a valid 10-digit phone number.")

            elif pw != cpw:

                st.error("Passwords do not match.")

            elif one(
                "SELECT id FROM users WHERE user_id=?",
                (uid.strip(),)
            ):

                st.error("User ID already exists.")

            else:

                exec_sql(
                    """
                    INSERT INTO users
                    (user_id,password_hash,role,name,phone,address)
                    VALUES(?,?,?,?,?,?)
                    """,
                    (
                        uid.strip(),
                        hash_pw(pw),
                        role,
                        name.strip(),
                        re.sub(r"\D", "", phone),
                        address.strip()
                    )
                )

                st.success(
                    "Account created successfully."
                )


# ============================================================
# HOME
# ============================================================

def home():

    logo = LOGO_DIR / "logo.png"

    if logo.exists():
        st.image(str(logo), width=110)

    st.markdown(
        f"""
        <div class="shopbar">
            <b>🛍️ KAIVANNAM</b>
            &nbsp; | &nbsp;
            {T("Craft Products")}
            •
            {T("Craft Traditions")}
            •
            {T("Artisans")}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <div class="hero">
            <h1>{T("Discover India Through Its Crafts")}</h1>
            <p>கைவண்ணம் | KAIVANNAM</p>
            <p>
            {T("Handmade traditions, regional stories and artisan-made products in one marketplace.")}
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        T("Craft Products"),
        one(
            "SELECT COUNT(*) n FROM products"
        )["n"]
    )

    c2.metric(
        T("States / Regions"),
        one(
            "SELECT COUNT(DISTINCT state) n FROM products"
        )["n"]
    )

    c3.metric(
        T("Craft Traditions"),
        one(
            "SELECT COUNT(DISTINCT craft_type) n FROM products"
        )["n"]
    )

    c4.metric(
        T("Artisans"),
        one(
            "SELECT COUNT(DISTINCT artisan) n FROM products"
        )["n"]
    )

    st.subheader(T("Quick Actions"))

    actions = [
        ("🛍️", "Shop Crafts", "Browse"),
        ("🤖", "AI Shopping", "AI Shopping Assistant"),
        ("🎙️", "Tamil Voice Search", "Voice Assistant"),
        ("❤️", "Wishlist", "Wishlist"),
        ("🛒", "My Cart", "Cart"),
        ("📦", "My Orders", "Orders"),
    ]

    cols = st.columns(6)

    for i, (icon, title, target) in enumerate(actions):

        with cols[i]:

            st.markdown(
                f"""
                <div class="quick-card">
                    <div style="font-size:28px">
                        {icon}
                    </div>
                    <b>{T(title)}</b>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button(
                T("Open"),
                key=f"quick_{i}",
                use_container_width=True
            ):

                st.session_state.page = target
                st.rerun()

    st.subheader(T("Featured Crafts"))

    rows = q(
        """
        SELECT * FROM products
        ORDER BY rating DESC,id
        LIMIT 8
        """
    )

    cols = st.columns(4)

    for i, r in enumerate(rows):

        with cols[i % 4]:
            product_card(r, "home")

    st.subheader(T("Explore by State"))

    states = [
        r["state"]
        for r in q(
            """
            SELECT DISTINCT state
            FROM products
            ORDER BY state
            """
        )
    ]

    cols = st.columns(4)

    for i, state in enumerate(states[:16]):

        if cols[i % 4].button(
            f"📍 {state}",
            key=f"state_{i}",
            use_container_width=True
        ):

            st.session_state.browse_state = state
            st.session_state.page = "Browse"
            st.rerun()


# ============================================================
# BROWSE
# ============================================================

def _normalized_search_text(value):
    value = (value or "").lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^\w\u0B80-\u0BFF\u0900-\u097F\u0C00-\u0C7F\u0D00-\u0D7F\u0C80-\u0CFF]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


SEARCH_STOPWORDS = {
    "give", "me", "show", "find", "get", "want", "need", "some",
    "the", "a", "an", "and", "or", "from", "in", "of", "for",
    "with", "on", "at", "to", "please", "products", "product",
    "craft", "crafts", "handicraft", "handicrafts", "items", "item",
    "பொருட்கள்", "பொருள்", "பொருட்களை", "காட்டு", "காட்டுங்கள்", "வேண்டும்",
    "traditional", "traditional crafts", "under", "below", "less",
    "than", "rupees", "rs", "show me",
}


def _catalog_search_context():
    """Read searchable values directly from the current product catalog.

    This keeps location/craft search generic: a new state, district, region,
    craft type, category or material added to the database becomes searchable
    automatically without another hard-coded if/else block.
    """
    values = {}
    for column in (
        "state", "district", "region", "craft_type", "category", "material"
    ):
        values[column] = [
            (r[column] or "").strip()
            for r in q(
                f"SELECT DISTINCT {column} FROM products "
                f"WHERE {column} IS NOT NULL AND TRIM({column})<>'' "
                f"ORDER BY {column}"
            )
            if (r[column] or "").strip()
        ]
    return values


def _extract_catalog_search(search):
    """Extract locations/crafts from natural-language search text."""
    text = _normalized_search_text(search)
    catalog = _catalog_search_context()

    detected = {
        "state": [],
        "district": [],
        "region": [],
        "craft_type": [],
        "category": [],
        "material": [],
    }

    for column, items in catalog.items():
        for item in items:
            item_norm = _normalized_search_text(item)
            if item_norm and (
                re.search(r"(?<!\w)" + re.escape(item_norm) + r"(?!\w)", text)
                or item_norm in text
            ):
                detected[column].append(item)

    # Keep the existing Tanjore/Thanjavur support while making all other
    # catalog locations dynamic as well.
    if "tanjore" in text or "thanjore" in text:
        if "Thanjavur" in catalog["district"]:
            detected["district"].append("Thanjavur")
        if "Tamil Nadu" in catalog["state"]:
            detected["state"].append("Tamil Nadu")

    for key in detected:
        detected[key] = list(dict.fromkeys(detected[key]))

    # Any meaningful leftover words can still be searched as product/name
    # terms, while common natural-language words are ignored.
    words = []
    for word in text.split():
        if word not in SEARCH_STOPWORDS and len(word) > 1:
            words.append(word)

    return detected, list(dict.fromkeys(words))


def ai_browse_image_keywords(uploaded_image):

    """Extract concise English catalog-search terms from a browse image."""
    client = ai_client()
    if not client or not uploaded_image:
        return []

    try:
        image_bytes = uploaded_image.getvalue()
        if not image_bytes:
            return []

        suffix = Path(getattr(uploaded_image, "name", "image.jpg")).suffix.lower()
        mime = (
            "image/png" if suffix == ".png"
            else "image/webp" if suffix == ".webp"
            else "image/jpeg"
        )
        encoded = base64.b64encode(image_bytes).decode("utf-8")

        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are KAIVANNAM marketplace visual search. "
                        "Return only a comma-separated list of up to 8 short English search terms "
                        "describing the visible craft/product: product type, craft type, category, "
                        "material, style, or distinctive design. Do not invent location or brand. "
                        "Use common catalog words such as pot, pottery, vase, basket, sari, painting, "
                        "toy, jewellery, wood carving, brass, bronze, bamboo, clay, textile when visible. "
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Identify the visible product and give useful catalog search keywords for this product image."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{encoded}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_completion_tokens=160
        )
        raw = (response.choices[0].message.content or "").strip()
        terms = []
        for term in re.split(r"[,\n]", raw):
            term = re.sub(r"^[\-*\d.) ]+", "", term).strip()
            if term and term.lower() not in {x.lower() for x in terms}:
                terms.append(term)

        # The uploaded filename is also a useful fallback for images such as
        # "pot.jpg" when the vision service is temporarily unavailable.
        filename_terms = re.findall(r"[A-Za-z]{3,}", Path(getattr(uploaded_image, "name", "")).stem)
        for term in filename_terms:
            if term.lower() not in {x.lower() for x in terms}:
                terms.append(term)
        return terms[:8]
    except Exception:
        filename_terms = re.findall(r"[A-Za-z]{3,}", Path(getattr(uploaded_image, "name", "")).stem)
        return filename_terms[:8]


def _visual_catalog_candidates(rows, seed_terms, max_candidates=160):
    """Rank live catalog rows using image-derived terms without broad fallback search."""
    terms = [str(x).strip() for x in (seed_terms or []) if str(x).strip()]
    generic = {
        "traditional", "contemporary", "handmade", "handcrafted", "craft", "crafted",
        "rustic", "decorative", "decoration", "style", "styled", "item", "product",
        "beautiful", "artisanal", "artisan", "design", "object", "traditional decor",
        "natural", "home", "indian", "indian craft"
    }

    def toks(value):
        text = _normalized_search_text(value or "")
        return {x for x in re.findall(r"[a-z0-9]+", text) if len(x) >= 3}

    term_sets = []
    for term in terms:
        ts = toks(term) - generic
        if ts:
            term_sets.append(ts)

    if not term_sets:
        return rows[:max_candidates]

    scored = []
    for row in rows:
        name_t = toks(row.get("name"))
        craft_t = toks(row.get("craft_type"))
        cat_t = toks(row.get("category"))
        mat_t = toks(row.get("material"))
        desc_t = toks(row.get("description"))
        all_t = name_t | craft_t | cat_t | mat_t | desc_t
        score = 0.0
        for ts in term_sets:
            score += 12 * len(ts & name_t)
            score += 9 * len(ts & craft_t)
            score += 9 * len(ts & cat_t)
            score += 6 * len(ts & mat_t)
            score += 2 * len(ts & desc_t)
            if ts & all_t:
                score += 1
        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda x: (-x[0], str(x[1].get("name") or "").lower()))
    return [row for _, row in scored[:max_candidates]]


def _vision_match_catalog(uploaded_image, candidates, mode="exact", limit=12):
    """Ask the vision model to choose only real catalog names."""
    client = ai_client()
    if not client or not uploaded_image or not candidates:
        return []
    try:
        image_bytes = uploaded_image.getvalue()
        if not image_bytes:
            return []
        suffix = Path(getattr(uploaded_image, "name", "image.jpg")).suffix.lower()
        mime = "image/png" if suffix == ".png" else "image/webp" if suffix == ".webp" else "image/jpeg"
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        catalog_lines = []
        for i, row in enumerate(candidates[:160], 1):
            catalog_lines.append(
                f"{i}. NAME={row.get('name') or ''} | CRAFT={row.get('craft_type') or ''} | "
                f"CATEGORY={row.get('category') or ''} | MATERIAL={row.get('material') or ''} | "
                f"DESCRIPTION={row.get('description') or ''}"
            )
        if mode == "exact":
            instruction = (
                "Return ONLY catalog NAME values for products that are the SAME product type/object "
                "shown in the image. A different object is not a match. Material/craft similarity alone "
                "is not enough. If there is no same product type in the catalog, return exactly NONE."
            )
        else:
            instruction = (
                "Return ONLY catalog NAME values that are meaningfully related to the image by product "
                "type, craft, or material. Do not return generic handmade/traditional products merely "
                "because they are crafts. If there are no meaningful related products, return exactly NONE."
            )
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": (
                    "You are KAIVANNAM marketplace visual search. " + instruction + " "
                    "Never invent a product name. Use only exact NAME values from the supplied live catalog. "
                    "Return one NAME per line, maximum 12, with no explanations."
                )},
                {"role": "user", "content": [
                    {"type": "text", "text": "LIVE CATALOG:\n" + "\n".join(catalog_lines)},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}}
                ]}
            ],
            temperature=0.0,
            max_completion_tokens=220
        )
        raw = (response.choices[0].message.content or "").strip()
        if not raw or raw.upper().strip() == "NONE":
            return []
        allowed = {str(row.get("name") or "").strip().lower(): str(row.get("name") or "").strip() for row in candidates}
        out = []
        for line in raw.splitlines():
            line = re.sub(r"^[\-*\d.) ]+", "", line).strip().strip('`').strip()
            if not line or line.upper() == "NONE":
                continue
            exact = allowed.get(line.lower())
            if exact and exact not in out:
                out.append(exact)
        return out[:limit]
    except Exception:
        return []


def ai_browse_image_exact_matches(uploaded_image, seed_terms=None, limit=12):
    """Return only same-product-type matches; no broad fallback."""
    try:
        rows = [dict(row) for row in q(
            """
            SELECT DISTINCT name, craft_type, category, material, description
            FROM products
            WHERE name IS NOT NULL AND TRIM(name)<>''
            ORDER BY name
            """
        )]
        if not rows:
            return []
        candidates = _visual_catalog_candidates(rows, seed_terms, 160)
        return _vision_match_catalog(uploaded_image, candidates, mode="exact", limit=limit)
    except Exception:
        return []


def ai_browse_related_matches(uploaded_image, seed_terms=None, limit=12):
    """Return related products only after the customer explicitly requests them."""
    try:
        rows = [dict(row) for row in q(
            """
            SELECT DISTINCT name, craft_type, category, material, description
            FROM products
            WHERE name IS NOT NULL AND TRIM(name)<>''
            ORDER BY name
            """
        )]
        if not rows:
            return []
        candidates = _visual_catalog_candidates(rows, seed_terms, 160)
        return _vision_match_catalog(uploaded_image, candidates, mode="related", limit=limit)
    except Exception:
        return []


def browse():

    st.title(f"🛍️ {T('Browse')}")

    voice_query = st.session_state.get(
        "voice_query",
        ""
    )

    if voice_query:
        st.info(
            f"🎤 {T('Voice Assistant')}: {voice_query}"
        )

    search = st.text_input(
        f"🔎 {T('Search product, craft, state, region, material or artisan')}",
        value=voice_query,
        key="browse_search"
    )

    # Customer visual search: on phones, Camera opens the live camera and
    # Upload opens the native gallery/file picker. Both feed the same Browse search.
    camera_photo = None
    gallery_photo = None
    image_search_col1, image_search_col2 = st.columns(2)

    with image_search_col1:
        camera_photo = st.camera_input(
            T("Take product photo"),
            key="customer_browse_camera"
        )

    with image_search_col2:
        gallery_photo = st.file_uploader(
            T("Choose product photo from Gallery"),
            type=["jpg", "jpeg", "png", "webp"],
            key="customer_browse_gallery"
        )

    browse_image = camera_photo or gallery_photo
    image_search_terms = []

    if browse_image:
        st.image(
            browse_image,
            caption=T("Selected product image"),
            width="stretch"
        )
        image_signature = f"{getattr(browse_image, 'name', 'camera')}:{getattr(browse_image, 'size', 0)}"
        if st.session_state.get("browse_image_signature") != image_signature:
            with st.spinner(T("Analyzing product image...")):
                image_search_terms = ai_browse_image_keywords(browse_image)
                image_match_names = ai_browse_image_exact_matches(
                    browse_image,
                    seed_terms=image_search_terms,
                    limit=12
                )
            st.session_state["browse_image_signature"] = image_signature
            st.session_state["browse_image_terms"] = image_search_terms
            st.session_state["browse_image_matches"] = image_match_names
            st.session_state["browse_related_matches"] = []
            st.session_state["browse_related_requested"] = False
        else:
            image_search_terms = st.session_state.get("browse_image_terms", [])
            image_match_names = st.session_state.get("browse_image_matches", [])

        if image_search_terms:
            st.info(
                f"🔍 {T('Visual search')}: " + ", ".join(image_search_terms)
            )
        if image_match_names:
            st.success(
                "🛍️ Matching products found in KAIVANNAM: "
                + ", ".join(image_match_names[:12])
            )
        else:
            st.warning("🔎 No product match found for this image.")
            if st.button("🔗 Show Related Products", key="browse_show_related"):
                with st.spinner("Finding related products from KAIVANNAM..."):
                    related_names = ai_browse_related_matches(
                        browse_image,
                        seed_terms=image_search_terms,
                        limit=12
                    )
                st.session_state["browse_related_matches"] = related_names
                st.session_state["browse_related_requested"] = True
                st.rerun()

            related_names = st.session_state.get("browse_related_matches", [])
            if related_names and st.session_state.get("browse_related_requested"):
                st.info(
                    "🔗 Related products: " + ", ".join(related_names[:12])
                )
    else:
        st.session_state.pop("browse_image_signature", None)
        st.session_state.pop("browse_image_terms", None)
        st.session_state.pop("browse_image_matches", None)
        st.session_state.pop("browse_related_matches", None)
        st.session_state.pop("browse_related_requested", None)

    states = [
        "All"
    ] + [
        r["state"]
        for r in q(
            """
            SELECT DISTINCT state
            FROM products
            ORDER BY state
            """
        )
    ]

    crafts = [
        "All"
    ] + [
        r["craft_type"]
        for r in q(
            """
            SELECT DISTINCT craft_type
            FROM products
            ORDER BY craft_type
            """
        )
    ]

    cats = [
        "All"
    ] + [
        r["category"]
        for r in q(
            """
            SELECT DISTINCT category
            FROM products
            ORDER BY category
            """
        )
    ]

    c1, c2, c3, c4 = st.columns(4)

    selected_state = st.session_state.get(
        "browse_state"
    )

    state = c1.selectbox(
        T("State"),
        states,
        index=(
            states.index(selected_state)
            if selected_state in states
            else 0
        )
    )

    craft = c2.selectbox(
        T("Craft"),
        crafts
    )

    category = c3.selectbox(
        T("Category"),
        cats
    )

    style = c4.selectbox(
        T("Style"),
        [
            "All",
            "Traditional",
            "Contemporary"
        ]
    )

    c5, c6 = st.columns(2)

    min_price = c5.number_input(
        T("Minimum price"),
        0.0,
        100000.0,
        0.0,
        step=100.0
    )

    max_price = c6.number_input(
        T("Maximum price"),
        0.0,
        100000.0,
        100000.0,
        step=100.0
    )

    where = []
    params = []

    image_only_search = (
        not search.strip()
        and bool(st.session_state.get("browse_image_terms"))
    )

    if image_only_search:
        search = " ".join(st.session_state.get("browse_image_terms", []))

    if search:

        search = re.sub(r"\s+", " ", search.strip())

        detected, leftover_words = _extract_catalog_search(search)

        # Location terms are applied as real database filters. This means
        # queries such as "Rajasthan products", "crafts from Gujarat",
        # "Jaipur handicrafts" and "products from Thanjavur" work without
        # hard-coding each possible judge question.
        location_clauses = []
        location_params = []

        for column in ("state", "district", "region"):
            values = detected[column]
            if values:
                placeholders = ",".join("?" for _ in values)
                location_clauses.append(
                    f"{column} IN ({placeholders})"
                )
                location_params.extend(values)

        if location_clauses:
            where.append(
                "(" + " OR ".join(location_clauses) + ")"
            )
            params.extend(location_params)

        # Craft/category/material terms are matched against the catalog.
        # Multiple detected terms are OR'ed so a natural request can return
        # all relevant products from the selected place.
        catalog_terms = []
        for column in ("craft_type", "category", "material"):
            catalog_terms.extend(detected[column])

        # Existing Tamil/English voice aliases continue to work for typed
        # requests as well.
        search_lower = search.lower()
        for tamil_word, aliases in VOICE_ALIASES.items():
            if tamil_word in search_lower:
                catalog_terms.extend(aliases)

        catalog_terms.extend(leftover_words)

        # When an image has produced real catalog matches, use those exact
        # product names as the primary Browse filter. Do not OR all visual
        # keywords into every catalog field because broad terms such as
        # "traditional", "handmade" or "clay" can otherwise return many
        # unrelated products.
        image_match_names = [
            str(name).strip()
            for name in st.session_state.get("browse_image_matches", [])
            if str(name).strip()
        ]
        if (
            not image_match_names
            and st.session_state.get("browse_related_requested")
        ):
            image_match_names = [
                str(name).strip()
                for name in st.session_state.get("browse_related_matches", [])
                if str(name).strip()
            ]
        if image_match_names and image_only_search:
            placeholders = ",".join("?" for _ in image_match_names)
            where.append(f"name IN ({placeholders})")
            params.extend(image_match_names)
        else:
            # For a normal typed search, keep the existing search behaviour.
            # Image keywords are never injected into an image-only search as a
            # broad OR query; image results must come from ranked catalog matches.
            if not image_match_names and not image_only_search:
                catalog_terms.extend(
                    st.session_state.get("browse_image_terms", [])
                )

        catalog_terms = list(dict.fromkeys(
            term.strip()
            for term in catalog_terms
            if term and term.strip()
        ))

        # An image search already has exact catalog-name constraints above.
        # Skip the broad text-search block in that case.
        if image_only_search and not image_match_names:
            where.append("1=0")
            st.info("🔎 No product match found for this image. Use **Show Related Products** to find similar products.")

        if catalog_terms and not (image_match_names and image_only_search):
            search_parts = []
            for _ in catalog_terms:
                search_parts.append(
                    """
                    (
                    name LIKE ?
                    OR craft_type LIKE ?
                    OR category LIKE ?
                    OR state LIKE ?
                    OR district LIKE ?
                    OR region LIKE ?
                    OR material LIKE ?
                    OR description LIKE ?
                    OR artisan LIKE ?
                    OR cultural_significance LIKE ?
                    )
                    """
                )

            # If a location was detected, leftover product/craft terms are
            # additionally constrained by that location. If there are no
            # product terms (e.g. "Rajasthan products"), the location filter
            # alone returns the state's catalog products.
            non_location_terms = []
            for term in catalog_terms:
                if not any(
                    _normalized_search_text(term) == _normalized_search_text(v)
                    for col in ("state", "district", "region")
                    for v in detected[col]
                ):
                    non_location_terms.append(term)

            if non_location_terms:
                search_parts = []
                for _ in non_location_terms:
                    search_parts.append(
                        """
                        (
                        name LIKE ?
                        OR craft_type LIKE ?
                        OR category LIKE ?
                        OR state LIKE ?
                        OR district LIKE ?
                        OR region LIKE ?
                        OR material LIKE ?
                        OR description LIKE ?
                        OR artisan LIKE ?
                        OR cultural_significance LIKE ?
                        )
                        """
                    )
                where.append(" OR ".join(search_parts))
                for term in non_location_terms:
                    params += [f"%{term}%"] * 10


    if state != "All":

        where.append("state=?")
        params.append(state)

    if craft != "All":

        where.append("craft_type=?")
        params.append(craft)

    if category != "All":

        where.append("category=?")
        params.append(category)

    if style != "All":

        where.append("style=?")
        params.append(style)

    where.append("price>=?")
    params.append(min_price)

    where.append("price<=?")
    params.append(max_price)

    sql = (
        "SELECT * FROM products WHERE "
        + " AND ".join(where)
        + " ORDER BY rating DESC,review_count DESC"
    )

    rows = q(sql, params)

    st.caption(
        f"{len(rows)} products found"
    )

    cols = st.columns(4)

    for i, r in enumerate(rows):

        with cols[i % 4]:
            product_card(r, "browse")


# ============================================================
# PRODUCT DETAILS
# ============================================================

def product_details():

    r = one(
        "SELECT * FROM products WHERE id=?",
        (
            st.session_state.get("detail_id"),
        )
    )

    if not r:

        st.warning(
            "Choose a product from Browse."
        )

        return

    r = dictrow(r)

    a, b = st.columns([1.1, 1])

    with a:

        st.image(
            str(product_image(r)),
            width="stretch"
        )

        st.caption(
            "Real craft photograph / source-linked catalog image"
        )

    with b:

        st.title(r["name"])

        st.markdown(
            f"**{r['craft_type']}** • "
            f"{r['state']} • "
            f"{r['district']}"
        )

        st.write(
            f"**{T('Artisans')}:** {r['artisan']}"
        )

        st.write(
            f"**{T('Material')}:** {r['material']}"
        )

        st.markdown(
            f"### ₹{r['price']:,.0f}"
        )

        st.write(
            f"⭐ {r['rating']:.1f} • "
            f"{r['review_count']} reviews • "
            f"{r['stock']} available"
        )

        st.write(
            r["description"]
        )

        st.info(
            r["cultural_significance"]
        )

        qty = st.number_input(
            T("Quantity"),
            1,
            max(1, int(r["stock"])),
            1,
            key=f"detail_qty_{r['id']}"
        )

        x, y, z = st.columns(3)

        if x.button(
            "❤️ Wishlist"
        ):

            add_wishlist(r["id"])
            st.toast("Added to wishlist")

        if y.button(
            "🛒 Add to Cart"
        ):

            add_cart(r["id"], qty)
            st.toast("Added to cart")

        if z.button(
            "⚡ Buy Now",
            type="primary"
        ):

            add_cart(r["id"], qty)
            st.session_state.page = "Checkout"
            st.rerun()

    st.subheader(
        T("The Story Behind This Craft")
    )

    story = one(
        """
        SELECT * FROM craft_stories
        WHERE craft=?
        """,
        (
            r["craft_type"],
        )
    )

    if story:

        st.write(
            f"**{T('Origin')}:** "
            f"{story['city']}, {story['state']}"
        )

        st.write(
            story["story"]
        )

        st.write(
            f"{story['experience']}+ years of artisan experience"
        )

    else:

        st.write(
            f"This {r['craft_type']} tradition "
            f"is connected with the cultural heritage "
            f"of {r['state']}."
        )

    st.subheader(
        T("Customer Reviews")
    )

    reviews = q(
        """
        SELECT * FROM reviews
        WHERE product_id=?
        ORDER BY id DESC
        LIMIT 10
        """,
        (
            r["id"],
        )
    )

    for review in reviews:

        st.write(
            f"⭐ {review['rating']} — "
            f"{review['review']}"
        )

    with st.form(
        f"review_{r['id']}"
    ):

        rating = st.slider(
            "Rating",
            1,
            5,
            5
        )

        text = st.text_area(
            "Your review"
        )

        if (
            st.form_submit_button(
                T("Submit Review")
            )
            and text.strip()
        ):

            exec_sql(
                """
                INSERT INTO reviews
                (user_id,product_id,rating,review)
                VALUES(?,?,?,?)
                """,
                (
                    current_user()["user_id"],
                    r["id"],
                    rating,
                    text.strip()
                )
            )

            avg = one(
                """
                SELECT AVG(rating) a,
                       COUNT(*) c
                FROM reviews
                WHERE product_id=?
                """,
                (
                    r["id"],
                )
            )

            exec_sql(
                """
                UPDATE products
                SET rating=?,review_count=?
                WHERE id=?
                """,
                (
                    round(avg["a"], 1),
                    avg["c"],
                    r["id"]
                )
            )

            st.success(
                "Review saved."
            )


# ============================================================
# WISHLIST
# ============================================================

def wishlist():

    st.title(
        f"❤️ {T('Wishlist')}"
    )

    rows = q(
        """
        SELECT p.*
        FROM wishlist w
        JOIN products p
        ON p.id=w.product_id
        WHERE w.user_id=?
        ORDER BY w.rowid DESC
        """,
        (
            current_user()["user_id"],
        )
    )

    if not rows:

        st.info(
            "Your wishlist is empty."
        )

        return

    cols = st.columns(4)

    for i, r in enumerate(rows):

        with cols[i % 4]:

            product_card(
                r,
                "wishlist"
            )

            if st.button(
                T("Remove"),
                key=f"remove_w_{r['id']}"
            ):

                remove_wishlist(r["id"])
                st.rerun()


# ============================================================
# CART
# ============================================================

def cart_page():

    st.title(
        f"🛒 {T('Your Cart')}"
    )

    rows = get_cart()

    if not rows:

        st.info(
            "Your cart is empty."
        )

        if st.button(
            T("Continue Shopping")
        ):

            st.session_state.page = "Browse"
            st.rerun()

        return

    subtotal = 0

    for r in rows:

        r = dictrow(r)

        a, b, c, d = st.columns(
            [1.1, 3.2, 1.1, 0.9]
        )

        with a:

            st.image(
                str(product_image(r)),
                width=110
            )

        with b:

            st.markdown(
                f"**{r['name']}**"
            )

            st.caption(
                f"{r['craft_type']} • "
                f"{r['state']} • "
                f"{r['artisan']}"
            )

            st.markdown(
                f"₹{r['price']:,.0f}"
            )

        with c:

            qty = st.number_input(
                T("Quantity"),
                1,
                99,
                int(r["quantity"]),
                key=f"qty_{r['id']}"
            )

            if qty != r["quantity"]:

                exec_sql(
                    """
                    UPDATE cart
                    SET quantity=?
                    WHERE user_id=?
                    AND product_id=?
                    """,
                    (
                        qty,
                        current_user()["user_id"],
                        r["id"]
                    )
                )

                st.rerun()

        with d:

            if st.button(
                T("Remove"),
                key=f"del_{r['id']}"
            ):

                exec_sql(
                    """
                    DELETE FROM cart
                    WHERE user_id=?
                    AND product_id=?
                    """,
                    (
                        current_user()["user_id"],
                        r["id"]
                    )
                )

                st.rerun()

        subtotal += (
            float(r["price"])
            * int(r["quantity"])
        )

        st.divider()

    delivery = (
        0
        if subtotal >= 999
        else 49
    )

    st.markdown(
        f"### {T('Price Details')}"
    )

    x, y, z = st.columns(3)

    x.metric(
        T("Items"),
        sum(
            int(r["quantity"])
            for r in rows
        )
    )

    y.metric(
        T("Subtotal"),
        f"₹{subtotal:,.0f}"
    )

    z.metric(
        T("Delivery"),
        T("FREE")
        if delivery == 0
        else f"₹{delivery:,.0f}"
    )

    st.markdown(
        f"## Total: ₹{subtotal+delivery:,.0f}"
    )

    a, b = st.columns(2)

    with a:

        if st.button(
            T("Continue Shopping")
        ):

            st.session_state.page = "Browse"
            st.rerun()

    with b:

        if st.button(
            T("Proceed to Checkout →"),
            type="primary"
        ):

            st.session_state.page = "Checkout"
            st.rerun()


# ============================================================
# CHECKOUT
# ============================================================

def checkout_page():

    st.title(
        f"🧾 {T('Checkout')}"
    )

    rows = get_cart()

    if not rows:

        st.info(
            "Your cart is empty."
        )

        return

    subtotal = sum(
        float(r["price"]) * int(r["quantity"])
        for r in rows
    )

    delivery = (
        0
        if subtotal >= 999
        else 49
    )

    st.markdown(
        f"### 1. {T('Delivery Address')}"
    )

    saved = q(
        """
        SELECT * FROM shipping_addresses
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (
            current_user()["user_id"],
        )
    )

    selected_saved = None

    if saved:

        options = [
            "+ Add a new address"
        ] + [
            f"{r['full_name']} • "
            f"{r['city']} • "
            f"{r['pincode']}"
            for r in saved
        ]

        choice = st.selectbox(
            T("Saved addresses"),
            options
        )

        if choice != "+ Add a new address":

            selected_saved = dictrow(
                saved[
                    options.index(choice) - 1
                ]
            )

    if selected_saved:

        address = selected_saved

        st.markdown(
            f"""
            <div class="address-card">
                <b>{address["full_name"]}</b><br>
                {address["line1"]}<br>
                {address.get("line2") or ""}<br>
                {address["city"]},
                {address["state"]} -
                {address["pincode"]}<br>
                📞 {address["phone"]}
            </div>
            """,
            unsafe_allow_html=True
        )

        edit_id = st.session_state.get("edit_address_id")

        if edit_id == address["id"]:
            with st.form(f"edit_delivery_address_{address['id']}"):
                c1, c2 = st.columns(2)
                edit_name = c1.text_input(T("Full Name"), value=address["full_name"])
                edit_phone = c2.text_input(T("Mobile Number"), value=address["phone"])
                edit_line1 = st.text_input("House / Flat / Street", value=address["line1"])
                edit_line2 = st.text_input("Area / Locality", value=address.get("line2") or "")
                c3, c4, c5 = st.columns(3)
                edit_city = c3.text_input(T("City"), value=address["city"])
                edit_state = c4.text_input(T("State"), value=address["state"])
                edit_pincode = c5.text_input(T("PIN Code"), value=address["pincode"])
                edit_landmark = st.text_input("Landmark", value=address.get("landmark") or "")
                ec1, ec2 = st.columns(2)
                save_edit = ec1.form_submit_button("💾 Save Address", type="primary")
                cancel_edit = ec2.form_submit_button("Cancel")

            if cancel_edit:
                st.session_state.pop("edit_address_id", None)
                st.rerun()

            if save_edit:
                clean_phone = re.sub(r"\D", "", edit_phone)
                if not all([edit_name.strip(), clean_phone, edit_line1.strip(), edit_city.strip(), edit_state.strip(), edit_pincode.strip()]):
                    st.error("Please fill all required fields.")
                    return
                if not re.fullmatch(r"[0-9]{10}", clean_phone):
                    st.error("Enter a valid 10-digit phone number.")
                    return
                if not edit_pincode.strip().isdigit() or len(edit_pincode.strip()) != 6:
                    st.error("Enter a valid 6-digit PIN.")
                    return

                exec_sql(
                    """
                    UPDATE shipping_addresses
                    SET full_name=?, phone=?, line1=?, line2=?, city=?, state=?, pincode=?, landmark=?
                    WHERE id=? AND user_id=?
                    """,
                    (
                        edit_name.strip(), clean_phone, edit_line1.strip(), edit_line2.strip(),
                        edit_city.strip(), edit_state.strip(), edit_pincode.strip(),
                        edit_landmark.strip(), address["id"], current_user()["user_id"]
                    )
                )
                st.session_state.pop("edit_address_id", None)
                st.session_state.checkout_address = {
                    "id": address["id"], "full_name": edit_name.strip(), "phone": clean_phone,
                    "line1": edit_line1.strip(), "line2": edit_line2.strip(),
                    "city": edit_city.strip(), "state": edit_state.strip(),
                    "pincode": edit_pincode.strip(), "landmark": edit_landmark.strip()
                }
                st.rerun()

        else:
            if st.button("✏️ Edit Address", key=f"edit_address_{address['id']}"):
                st.session_state.edit_address_id = address["id"]
                st.rerun()

        st.session_state.checkout_address = address

    else:

        registered_name = str(current_user().get("name") or "")
        registered_phone = str(current_user().get("phone") or "")
        registered_address = str(current_user().get("address") or "")

        with st.form(
            "delivery_address"
        ):

            c1, c2 = st.columns(2)

            full_name = c1.text_input(
                T("Full Name"),
                value=registered_name
            )

            phone = c2.text_input(
                T("Mobile Number"),
                value=registered_phone
            )

            line1 = st.text_input(
                "House / Flat / Street",
                value=registered_address
            )

            line2 = st.text_input(
                "Area / Locality"
            )

            c3, c4, c5 = st.columns(3)

            city = c3.text_input(
                T("City")
            )

            state = c4.text_input(
                T("State"),
                value="Tamil Nadu"
            )

            pincode = c5.text_input(
                T("PIN Code")
            )

            landmark = st.text_input(
                "Landmark"
            )

            save_address = st.checkbox(
                T(
                    "Save this address for future orders"
                ),
                value=True
            )

            submitted = st.form_submit_button(
                T("Continue to Payment"),
                type="primary"
            )

        address = {
            "full_name": full_name.strip(),
            "phone": phone.strip(),
            "line1": line1.strip(),
            "line2": line2.strip(),
            "city": city.strip(),
            "state": state.strip(),
            "pincode": pincode.strip(),
            "landmark": landmark.strip()
        }

        if submitted:

            if not all([
                address["full_name"],
                address["phone"],
                address["line1"],
                address["city"],
                address["state"],
                address["pincode"]
            ]):

                st.error(
                    "Please fill all required fields."
                )

                return

            if (
                not address["pincode"].isdigit()
                or len(address["pincode"]) != 6
            ):

                st.error(
                    "Enter a valid 6-digit PIN."
                )

                return

            if save_address:

                exec_sql(
                    """
                    INSERT INTO shipping_addresses
                    (
                    user_id,full_name,phone,line1,
                    line2,city,state,pincode,landmark
                    )
                    VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        current_user()["user_id"],
                        address["full_name"],
                        address["phone"],
                        address["line1"],
                        address["line2"],
                        address["city"],
                        address["state"],
                        address["pincode"],
                        address["landmark"]
                    )
                )

            st.session_state.checkout_address = address

            st.rerun()

        if not st.session_state.get(
            "checkout_address"
        ):
            return

        address = st.session_state.checkout_address

    if not st.session_state.get(
        "checkout_address"
    ):
        return

    address = st.session_state.checkout_address

    st.markdown(
        f"### 2. {T('Order Summary')}"
    )

    for r in rows:

        st.write(
            f"**{r['name']}** × "
            f"{r['quantity']} — "
            f"₹{float(r['price']) * int(r['quantity']):,.0f}"
        )

    st.markdown(
        f"### 3. {T('Offers')}"
    )

    coupon = st.selectbox(
        T("Apply coupon"),
        [
            "No coupon",
            "KAIVANNAM10 — 10% off up to ₹300",
            "CRAFT50 — ₹50 off"
        ]
    )

    if coupon.startswith(
        "KAIVANNAM10"
    ):

        discount = min(
            subtotal * 0.10,
            300
        )

        coupon_code = "KAIVANNAM10"

    elif coupon.startswith(
        "CRAFT50"
    ):

        discount = (
            50
            if subtotal >= 500
            else 0
        )

        coupon_code = (
            "CRAFT50"
            if discount
            else ""
        )

    else:

        discount = 0
        coupon_code = ""

    grand_total = max(
        0,
        subtotal + delivery - discount
    )

    st.markdown(
        f"""
        <div class="order-total">
            <b>{T("Subtotal")}:</b>
            ₹{subtotal:,.0f}<br>

            <b>{T("Delivery")}:</b>
            {"FREE" if delivery == 0 else f"₹{delivery:,.0f}"}<br>

            <b>Discount:</b>
            -₹{discount:,.0f}

            <hr>

            <h3>
                Total: ₹{grand_total:,.0f}
            </h3>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        f"### 4. {T('Payment')}"
    )

    method = st.radio(
        T("Choose payment method"),
        [
            "UPI",
            "Debit / Credit Card",
            "Net Banking",
            "Cash on Delivery"
        ],
        horizontal=True
    )

    payment_verified = False
    razorpay_payment_id = ""
    razorpay_order_id = ""

    # Real Razorpay checkout for UPI / Card / Net Banking.
    # The Razorpay secret stays only in api.py; it is never exposed here.
    if method != "Cash on Delivery":
        try:
            payment_api_url = ""
            if hasattr(st, "secrets"):
                try:
                    payment_api_url = str(st.secrets.get("PAYMENT_API_URL", "")).strip()
                except Exception:
                    payment_api_url = ""
            payment_api_url = payment_api_url or os.getenv("PAYMENT_API_URL", "http://localhost:8000")

            payment_state = st.session_state.get("razorpay_checkout", {})
            if payment_state.get("grand_total") != float(grand_total):
                payment_state = {}
                st.session_state.pop("razorpay_checkout", None)

            if not payment_state:
                if st.button("💳 Pay securely with Razorpay", type="primary", key="create_razorpay_order"):
                    try:
                        api_response = requests.post(
                            payment_api_url.rstrip("/") + "/razorpay/order",
                            json={
                                "amount": float(grand_total),
                                "receipt": f"KV-{current_user()['user_id']}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                                "notes": {"user_id": current_user()["user_id"]}
                            },
                            timeout=20
                        )
                        api_response.raise_for_status()
                        order_data = api_response.json()
                        st.session_state.razorpay_checkout = {
                            "order_id": order_data["id"],
                            "key_id": order_data["key_id"],
                            "grand_total": float(grand_total),
                            "payment_api_url": payment_api_url.rstrip("/"),
                        }
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Unable to start secure payment: {exc}")

            payment_state = st.session_state.get("razorpay_checkout", {})
            if payment_state:
                checkout_order_id = payment_state.get("order_id", "")
                checkout_key_id = payment_state.get("key_id", "")
                checkout_amount = int(round(float(grand_total) * 100))
                checkout_html = f"""
                <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
                <button id="paybtn" style="background:#6b2337;color:white;border:0;border-radius:8px;padding:12px 20px;font-size:16px;cursor:pointer;">
                    Pay ₹{float(grand_total):,.2f} securely
                </button>
                <script>
                const options = {{
                    key: {checkout_key_id!r},
                    amount: {checkout_amount},
                    currency: "INR",
                    name: "KAIVANNAM",
                    description: "KAIVANNAM artisan order",
                    order_id: {checkout_order_id!r},
                    theme: {{color: "#6b2337"}},
                    handler: function (response) {{
                        const base = window.parent.location.href.split('?')[0] + '?payment_return=1';
                        const join = '&';
                        const url = base + join +
                            'razorpay_payment_id=' + encodeURIComponent(response.razorpay_payment_id) +
                            '&razorpay_order_id=' + encodeURIComponent(response.razorpay_order_id) +
                            '&razorpay_signature=' + encodeURIComponent(response.razorpay_signature);
                        window.parent.location.href = url;
                    }}
                }};
                const rzp = new Razorpay(options);
                document.getElementById('paybtn').onclick = function(e) {{ rzp.open(); e.preventDefault(); }};
                </script>
                """
                components.html(checkout_html, height=70)
                st.caption("Razorpay securely supports the payment methods enabled on your account, including UPI, cards and net banking.")

        except Exception as exc:
            st.error(f"Payment setup error: {exc}")

    else:
        st.info("💵 Cash on Delivery selected — pay the delivery person when your order arrives.")

    # Payment callback is verified by the backend before an online order is placed.
    callback_payment_id = st.query_params.get("razorpay_payment_id")
    callback_order_id = st.query_params.get("razorpay_order_id")
    callback_signature = st.query_params.get("razorpay_signature")
    if callback_payment_id and callback_order_id and callback_signature:
        try:
            payment_api_url = st.session_state.get("razorpay_checkout", {}).get("payment_api_url")
            if not payment_api_url:
                try:
                    payment_api_url = str(st.secrets.get("PAYMENT_API_URL", "")).strip()
                except Exception:
                    payment_api_url = ""
            payment_api_url = payment_api_url or os.getenv("PAYMENT_API_URL", "http://localhost:8000")
            verify_response = requests.post(
                payment_api_url.rstrip("/") + "/razorpay/verify",
                json={
                    "razorpay_order_id": callback_order_id,
                    "razorpay_payment_id": callback_payment_id,
                    "razorpay_signature": callback_signature
                },
                timeout=20
            )
            verify_response.raise_for_status()
            payment_verified = bool(verify_response.json().get("verified"))
            razorpay_payment_id = callback_payment_id
            razorpay_order_id = callback_order_id
            if payment_verified:
                st.success("✅ Payment successful and verified.")
                st.session_state.razorpay_payment_verified = True
                st.session_state.razorpay_payment_id = callback_payment_id
                st.session_state.razorpay_order_id = callback_order_id
                st.session_state.pop("razorpay_checkout", None)
                try:
                    st.query_params.clear()
                except Exception:
                    pass
        except Exception as exc:
            st.error(f"Payment verification failed: {exc}")

    payment_verified = payment_verified or bool(st.session_state.get("razorpay_payment_verified"))
    if method != "Cash on Delivery" and not payment_verified:
        st.caption("Complete the Razorpay payment first. The order will be placed only after successful verification.")

    if st.button(
        f"🔒 {T('Place Order')}",
        type="primary",
        disabled=(method != "Cash on Delivery" and not payment_verified)
    ):

        rows = get_cart()

        oid = exec_sql(
            """
            INSERT INTO orders(
                user_id,total,status,
                payment_method,payment_status,
                shipping_name,shipping_phone,
                shipping_address,
                shipping_city,
                shipping_state,
                shipping_pincode,
                shipping_landmark,
                subtotal,
                delivery_charge,
                discount,
                coupon_code
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                current_user()["user_id"],
                grand_total,
                "Order Placed",
                method,
                ("Pending - Cash on Delivery" if method == "Cash on Delivery" else "Paid"),
                address["full_name"],
                address["phone"],
                address["line1"]
                + (
                    ", " + address["line2"]
                    if address.get("line2")
                    else ""
                ),
                address["city"],
                address["state"],
                address["pincode"],
                address.get("landmark", ""),
                subtotal,
                delivery,
                discount,
                coupon_code
            )
        )

        for r in rows:

            exec_sql(
                """
                INSERT INTO order_items
                (order_id,product_id,quantity,price)
                VALUES(?,?,?,?)
                """,
                (
                    oid,
                    r["id"],
                    r["quantity"],
                    r["price"]
                )
            )

            exec_sql(
                """
                UPDATE products
                SET stock=MAX(0,stock-?)
                WHERE id=?
                """,
                (
                    r["quantity"],
                    r["id"]
                )
            )

        exec_sql(
            """
            INSERT INTO payments
            (order_id,method,status,amount)
            VALUES(?,?,?,?)
            """,
            (
                oid,
                method,
                ("Pending - Cash on Delivery" if method == "Cash on Delivery" else "Paid"),
                grand_total
            )
        )

        exec_sql(
            """
            INSERT INTO delivery_tracking
            (order_id,status,event_time)
            VALUES(?,?,?)
            """,
            (
                oid,
                "Order Placed",
                datetime.now().isoformat()
            )
        )

        exec_sql(
            """
            DELETE FROM cart
            WHERE user_id=?
            """,
            (
                current_user()["user_id"],
            )
        )

        st.session_state.pop(
            "checkout_address",
            None
        )

        st.session_state.last_order_id = oid
        st.session_state.page = "Orders"

        st.rerun()


# ============================================================
# ORDERS
# ============================================================

def orders():

    st.title(
        f"📦 {T('My Orders')}"
    )

    if st.session_state.get(
        "last_order_id"
    ):

        oid = st.session_state.pop(
            "last_order_id"
        )

        st.success(
            f"Order #{oid} placed successfully!"
        )

    rows = q(
        """
        SELECT *
        FROM orders
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (
            current_user()["user_id"],
        )
    )

    if not rows:

        st.info(
            "No orders yet."
        )

        return

    for order in rows:

        order = dictrow(order)

        with st.container(
            border=True
        ):

            st.markdown(
                f"### Order #{order['id']} • "
                f"₹{order['total']:,.0f}"
            )

            st.caption(
                f"Status: {order['status']} • "
                f"Payment: {order.get('payment_method')}"
            )

            if order.get("shipping_name"):
                st.markdown("**📍 Delivery Address**")
                address_lines = [
                    order.get("shipping_name", ""),
                    order.get("shipping_address", ""),
                    ", ".join([x for x in [order.get("shipping_city", ""), order.get("shipping_state", "")] if x])
                    + (f" - {order.get('shipping_pincode', '')}" if order.get("shipping_pincode") else ""),
                    (f"Landmark: {order.get('shipping_landmark')}" if order.get("shipping_landmark") else ""),
                    (f"📞 {order.get('shipping_phone')}" if order.get("shipping_phone") else "")
                ]
                st.write("\n".join(x for x in address_lines if x))

            tracking = q(
                """
                SELECT status,event_time
                FROM delivery_tracking
                WHERE order_id=?
                ORDER BY id ASC
                """,
                (order["id"],)
            )
            if tracking:
                with st.expander("🚚 Track Order", expanded=True):
                    for event in tracking:
                        when = str(event["event_time"] or "").replace("T", " ")[:16]
                        marker = "🟢" if event["status"] == order["status"] else "⚪"
                        st.write(f"{marker} **{event['status']}** — {when}")

            items = q(
                """
                SELECT oi.*,p.name,
                       p.image_path,
                       p.image_key,
                       p.craft_type,
                       p.state
                FROM order_items oi
                JOIN products p
                ON p.id=oi.product_id
                WHERE oi.order_id=?
                """,
                (
                    order["id"],
                )
            )

            cols = st.columns(
                min(
                    4,
                    max(
                        1,
                        len(items)
                    )
                )
            )

            for i, item in enumerate(items):

                with cols[
                    i % len(cols)
                ]:

                    st.image(
                        str(
                            product_image(item)
                        ),
                        width="stretch"
                    )

                    st.caption(
                        f"{item['name']} × "
                        f"{item['quantity']}"
                    )

            current_index = (
                STATUSES.index(
                    order["status"]
                )
                if order["status"]
                in STATUSES
                else 0
            )

            for i, status in enumerate(
                STATUSES
            ):

                icon = (
                    "🟢"
                    if i <= current_index
                    else "⚪"
                )

                st.write(
                    f"{icon} **{status}**"
                )

            # Return an item after delivery. The return request is tied to the exact order item.
            if order["status"] == "Delivered":
                st.markdown("**↩️ Return eligible items**")
                for return_item in items:
                    existing_return = one(
                        "SELECT id,status FROM return_requests WHERE order_id=? AND order_item_id=? ORDER BY id DESC LIMIT 1",
                        (order["id"], return_item["id"])
                    )
                    if existing_return:
                        st.caption(f"{return_item['name']}: Return request — {existing_return['status']}")
                        continue
                    return_reason = st.selectbox(
                        "Reason",
                        ["Wrong item", "Damaged item", "Defective item", "Item not as described", "Other"],
                        key=f"return_reason_{order['id']}_{return_item['id']}"
                    )
                    if st.button(
                        f"↩️ Request return — {return_item['name']}",
                        key=f"request_return_{order['id']}_{return_item['id']}"
                    ):
                        exec_sql(
                            """
                            INSERT INTO return_requests
                            (order_id,order_item_id,user_id,reason,status,refund_status)
                            VALUES(?,?,?,?,?,?)
                            """,
                            (
                                order["id"],
                                return_item["id"],
                                current_user()["user_id"],
                                return_reason,
                                "Requested",
                                "Pending"
                            )
                        )
                        st.success("Return request submitted successfully.")
                        st.rerun()

            if st.button(
                T("Buy these again"),
                key=f"reorder_{order['id']}"
            ):

                for item in items:

                    add_cart(
                        item["product_id"],
                        int(item["quantity"])
                    )

                st.session_state.page = "Cart"
                st.rerun()


# ============================================================
# STORIES
# ============================================================

def generate_craft_story_from_image_bytes(image_bytes):
    """Generate a craft story from exactly the uploaded image bytes."""
    client = ai_client()
    if not client or not image_bytes:
        return ""

    try:
        from PIL import Image, ImageOps
        from io import BytesIO

        image = Image.open(BytesIO(image_bytes))
        image = ImageOps.exif_transpose(image).convert("RGB")
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=92)
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

        language = {
            "English": "English",
            "தமிழ்": "Tamil (தமிழ்)",
            "हिन्दी": "Hindi (हिन्दी)",
            "മലയാളം": "Malayalam (മലയാളം)",
            "తెలుగు": "Telugu (తెలుగు)",
            "ಕನ್ನಡ": "Kannada (ಕನ್ನಡ)"
        }.get(current_lang(), "English")

        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are KAIVANNAM's Craft Story assistant. "
                        f"Write the story only in {language}. "
                        "Analyze ONLY the single image supplied by the user. "
                        "Use only visible details from that image. "
                        "Do not use any other image, product, database, seller details, "
                        "customer details, memory, or unrelated information. "
                        "Do not invent an artisan name, exact location, history, date, "
                        "heritage claim, or unsupported fact. "
                        "Return only a short presentation-ready craft story."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Generate the craft story for THIS uploaded image only."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_completion_tokens=700
        )
        return (response.choices[0].message.content or "").strip()
    except Exception:
        return ""


def stories():

    st.title(
        f"📖 {T('Craft Stories')}"
    )

    st.markdown(
        "Upload an image. The story will be created only from the image you upload."
    )

    upload = st.file_uploader(
        "📷 Upload craft/product image",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=False,
        key="craft_story_image"
    )

    if not upload:
        st.info("Please upload an image to generate its craft story.")
        return

    image_bytes = upload.getvalue()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    st.image(
        image,
        caption="Uploaded craft image",
        width="stretch"
    )

    if st.button(
        "✨ Generate Craft Story",
        type="primary",
        key="generate_uploaded_craft_story"
    ):
        with st.spinner("🔎 Analyzing the uploaded image..."):
            story = generate_craft_story_from_image_bytes(image_bytes)

        if story:
            st.subheader("📖 Craft Story")
            st.write(story)
        else:
            st.warning("No story could be generated from this image. Please check the AI connection.")


def heritage_map():

    st.title(
        f"🗺️ {T('India Craft Heritage Map')}"
    )

    # INDIA ONLY CRAFT LOCATIONS
    pts = [

        ("Thanjavur", "Tamil Nadu",
         10.79, 79.14, "Thanjavur Painting"),

        ("Swamimalai", "Tamil Nadu",
         10.95, 79.34, "Swamimalai Bronze"),

        ("Mahabalipuram", "Tamil Nadu",
         12.62, 80.19, "Stone Craft"),

        ("Aranmula", "Kerala",
         9.33, 76.68, "Aranmula Mirror"),

        ("Channapatna", "Karnataka",
         12.65, 77.20, "Channapatna Toys"),

        ("Mysuru", "Karnataka",
         12.30, 76.65, "Mysore Painting"),

        ("Machilipatnam", "Andhra Pradesh",
         16.18, 81.13, "Kalamkari"),

        ("Kondapalli", "Andhra Pradesh",
         16.62, 80.54, "Kondapalli Toys"),

        ("Jaipur", "Rajasthan",
         26.91, 75.79, "Blue Pottery"),

        ("Kutch", "Gujarat",
         23.73, 69.86, "Kutch Embroidery"),

        ("Puri", "Odisha",
         19.81, 85.83, "Pattachitra"),

        ("Cuttack", "Odisha",
         20.46, 85.88, "Silver Filigree"),

        ("Madhubani", "Bihar",
         26.35, 86.07, "Madhubani Painting"),

        ("Srinagar", "Jammu & Kashmir",
         34.08, 74.80, "Kashmiri Papier-Mâché"),

        ("Guwahati", "Assam",
         26.14, 91.74, "Assam Bamboo Craft"),

        ("Bishnupur", "West Bengal",
         23.07, 87.32, "Bengal Terracotta"),

        ("Lucknow", "Uttar Pradesh",
         26.85, 80.95, "Chikankari"),

        ("Varanasi", "Uttar Pradesh",
         25.32, 82.97, "Silk Weaving"),

        ("Patiala", "Punjab",
         30.34, 76.39, "Phulkari"),

        ("Palghar", "Maharashtra",
         19.69, 72.77, "Warli Art"),

        ("Paithan", "Maharashtra",
         19.48, 75.38, "Paithani"),

        ("Bastar", "Chhattisgarh",
         19.10, 81.95, "Bastar Bell Metal"),

        ("Hazaribagh", "Jharkhand",
         23.99, 85.36, "Sohrai Art"),

        ("Kullu", "Himachal Pradesh",
         31.96, 77.10, "Wool Craft"),

        ("Almora", "Uttarakhand",
         29.59, 79.65, "Ringaal Craft"),

        ("Kohima", "Nagaland",
         25.67, 94.11, "Naga Craft"),

        ("Shillong", "Meghalaya",
         25.58, 91.89, "Bamboo Craft"),

        ("Aizawl", "Mizoram",
         23.73, 92.72, "Mizo Weaving"),

        ("Gangtok", "Sikkim",
         27.33, 88.61, "Lepcha Weaving"),

        ("Agartala", "Tripura",
         23.83, 91.28, "Bamboo Craft"),
    ]

    df = pd.DataFrame(
        pts,
        columns=[
            "Place",
            "State",
            "Latitude",
            "Longitude",
            "Craft"
        ]
    )

    fig = px.scatter_geo(
        df,
        lat="Latitude",
        lon="Longitude",
        hover_name="Place",
        hover_data=[
            "State",
            "Craft"
        ],
        projection="natural earth",
        height=650
    )

    # Keep India as the visual focus
    fig.update_geos(
        center={
            "lat": 22.5,
            "lon": 79.0
        },
        projection_scale=4.7,
        showland=True,
        showcountries=True,
        countrycolor="#b89b72",
        showocean=True,
        showlakes=True
    )

    fig.update_layout(
        margin=dict(
            l=0,
            r=0,
            t=0,
            b=0
        )
    )

    st.plotly_chart(
        fig,
        width="stretch"
    )

    st.subheader(
        "🇮🇳 Indian Craft Regions"
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# AI SHOPPING
# ============================================================

def ai_shopping():

    st.title(
        f"🤖 {T('AI Shopping Assistant')}"
    )

    st.info(
        ai_mode()
    )

    prompt = st.text_area(
        T(
            "Ask in English, தமிழ், हिन्दी, മലയാളം, తెలుగు or ಕನ್ನಡ"
        ),
        placeholder=(
            "Show me traditional crafts from Rajasthan under ₹2000"
        )
    )

    if st.button(
        T("Find Crafts"),
        type="primary"
    ) and prompt.strip():

        live = ai_call(
            f"""
            User language: {current_lang()}

            User request:
            {prompt}

            Suggest matching categories or products,
            but do not invent products.
            """
        )

        if live:
            st.write(live)

        text = prompt.lower()

        rows = [
            dictrow(r)
            for r in q(
                """
                SELECT *
                FROM products
                ORDER BY rating DESC
                """
            )
        ]

        mapping = {
            "rajasthan": "Rajasthan",
            "राजस्थान": "Rajasthan",
            "tamil": "Tamil Nadu",
            "தமிழ்": "Tamil Nadu",
            "தஞ்சாவூர்": "Tamil Nadu",
            "kerala": "Kerala",
            "കേരള": "Kerala",
            "odisha": "Odisha",
            "pattachitra": "Odisha",
            "karnataka": "Karnataka",
            "gujarat": "Gujarat",
            "bihar": "Bihar",
            "kashmir": "Jammu & Kashmir"
        }

        for key, value in mapping.items():

            if key in text:

                rows = [
                    r
                    for r in rows
                    if r["state"] == value
                ]

                break

        match = re.search(
            r"(?:under|below|less than|₹)\s*(?:₹)?\s*([0-9,]+)",
            text
        )

        if match:

            limit = float(
                match.group(1).replace(",", "")
            )

            rows = [
                r
                for r in rows
                if r["price"] <= limit
            ]

        if not rows:

            st.warning(
                "No matching products found."
            )

        else:

            st.subheader(
                T("Matching products from SQLite catalog")
            )

            cols = st.columns(4)

            for i, r in enumerate(rows[:12]):

                with cols[i % 4]:
                    product_card(
                        r,
                        "ai"
                    )


# ============================================================
# VOICE ASSISTANT
# ============================================================

def normalize_voice_query(text):
    """Normalize common Tamil/English Whisper variants without changing normal speech."""
    value = re.sub(r"\s+", " ", (text or "").strip())
    if not value:
        return ""
    for source, target in sorted(VOICE_NORMALIZATION.items(), key=lambda item: len(item[0]), reverse=True):
        value = re.sub(rf"(?<![\w\u0B80-\u0BFF]){re.escape(source)}(?![\w\u0B80-\u0BFF])", target, value, flags=re.IGNORECASE)
    return value


def resolve_voice_to_catalog(recognized_text, client):
    """Resolve spoken text against every product currently in the catalog.

    The catalog is the source of truth.  Matching is done in layers so that
    exact names, phonetic spellings, translated product words, and mixed-
    language speech can all reach the existing Browse search without changing
    the rest of the application.
    """
    text = normalize_voice_query(recognized_text)
    if not text:
        return ""

    try:
        rows = q(
            """
            SELECT DISTINCT name, craft_type, category, material, state, district,
                            region, description, artisan
            FROM products
            WHERE name IS NOT NULL AND TRIM(name)<>''
            ORDER BY name
            """
        )

        catalog = []
        seen = set()
        for row in rows:
            name = (row["name"] or "").strip()
            key = name.casefold()
            if not name or key in seen:
                continue
            seen.add(key)
            catalog.append({
                "name": name,
                "craft": (row["craft_type"] or "").strip(),
                "category": (row["category"] or "").strip(),
                "material": (row["material"] or "").strip(),
                "state": (row["state"] or "").strip(),
                "district": (row["district"] or "").strip(),
                "region": (row["region"] or "").strip(),
                "description": (row["description"] or "").strip(),
                "artisan": (row["artisan"] or "").strip(),
            })

        if not catalog:
            return text

        text_norm = _normalized_search_text(text)

        # Whisper can occasionally mis-hear a short Tamil craft phrase such as
        # “மண்பானைகள்” as the English filler phrase “one point”.  In this
        # marketplace context that is a transcription artefact, not a product
        # request, so resolve it deterministically before any AI matching.
        voice_hallucination_aliases = {
            "one point": ["clay pot", "earthen pot", "pottery", "terracotta", "pot"],
            "onepoint": ["clay pot", "earthen pot", "pottery", "terracotta", "pot"],
            "1 point": ["clay pot", "earthen pot", "pottery", "terracotta", "pot"],
        }
        if text_norm in voice_hallucination_aliases:
            return " ".join(voice_hallucination_aliases[text_norm])

        # Deterministic Tamil craft matching: do not send common product words
        # through the chat model. This prevents outputs such as "1. ..." or
        # explanatory text from becoming the Browse search query.
        direct_voice_aliases = {
            "மண் பானை": ["clay pot", "earthen pot", "pottery", "terracotta", "pot"],
            "மண் பானைகள்": ["clay pot", "earthen pot", "pottery", "terracotta", "pot"],
            "மண்பானை": ["clay pot", "earthen pot", "pottery", "terracotta", "pot"],
            "மண்பானைகள்": ["clay pot", "earthen pot", "pottery", "terracotta", "pot"],
            "பானைகள்": ["pot", "clay pot", "earthen pot", "pottery", "terracotta"],
            "களிமண் பானை": ["clay pot", "earthen pot", "pottery", "terracotta", "pot"],
            "களிமண் பானைகள்": ["clay pot", "earthen pot", "pottery", "terracotta", "pot"],
        }
        for tamil_phrase, search_terms in direct_voice_aliases.items():
            if tamil_phrase in text:
                return " ".join(search_terms)

        # Deterministic category/craft requests. These are broad marketplace
        # requests, so keep the search term broad enough for Browse to return
        # all matching catalog products rather than one arbitrary item.
        broad_voice_aliases = {
            "பானை": "pot clay pot earthen pot pottery terracotta",
            "பானைகள்": "pot clay pot earthen pot pottery terracotta",
            "மண்பானை": "clay pot earthen pot pottery terracotta",
            "மண்பானைகள்": "clay pot earthen pot pottery terracotta",
            "புடவை": "sari saree textile silk cotton weaving handloom",
            "புடவைகள்": "sari saree textile silk cotton weaving handloom",
            "சேலை": "sari saree textile silk cotton weaving handloom",
            "சேலைகள்": "sari saree textile silk cotton weaving handloom",
            "கூடை": "basket basketry bamboo cane",
            "கூடைகள்": "basket basketry bamboo cane",
            "குடுவை": "pot vase water pot clay pot pottery terracotta container",
            "குடுவைகள்": "pot vase water pot clay pot pottery terracotta container",
            "குடவைகள்": "pot vase water pot clay pot pottery terracotta container",
            "தஞ்சாவூர் பொருட்கள்": "thanjavur tanjore painting dolls metal relief",
            "தஞ்சை பொருட்கள்": "thanjavur tanjore painting dolls metal relief",
            "கைவினை பொருட்கள்": "handmade artisan handicraft craft",
            "கைவினைப் பொருட்கள்": "handmade artisan handicraft craft",
            "க்ராஃப்ட் பொருட்கள்": "handmade artisan handicraft craft",
            "கிராஃப்ட் பொருட்கள்": "handmade artisan handicraft craft",
        }
        for phrase, search_terms in broad_voice_aliases.items():
            if text_norm == _normalized_search_text(phrase):
                return search_terms

        # Exact catalog match first.  This handles names such as
        # "Traditional Decor Piece – Thanjavur Painting" with zero AI calls.
        for item in catalog:
            if _normalized_search_text(item["name"]) == text_norm:
                return item["name"]

        # Direct substring match is useful when the user says only part of a
        # product name, e.g. "Traditional Decor Piece".
        direct = []
        for item in catalog:
            name_norm = _normalized_search_text(item["name"])
            if name_norm and (name_norm in text_norm or text_norm in name_norm):
                direct.append(item)
        if direct:
            # If the spoken text is a shared variant such as "Traditional
            # Decor Piece", keep it as a search term so all matching products
            # are shown rather than forcing the first database row.
            shared_name = text_norm
            shared_count = sum(
                1 for item in catalog
                if shared_name and shared_name in _normalized_search_text(item["name"])
            )
            if shared_count > 1:
                return text
            return direct[0]["name"]

        # Lightweight phonetic/word-overlap candidates reduce the multilingual
        # AI prompt to a small set while still considering the whole catalog.
        import difflib
        text_words = set(text_norm.split())
        scored = []
        for item in catalog:
            name_norm = _normalized_search_text(item["name"])
            if not name_norm:
                continue
            name_words = set(name_norm.split())
            overlap = len(text_words & name_words)
            ratio = difflib.SequenceMatcher(None, text_norm, name_norm).ratio()
            token_ratio = (
                overlap / max(1, len(text_words | name_words))
            )
            score = (overlap * 2.0) + ratio + token_ratio
            if score > 0.45:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        local_candidates = [item for _, item in scored[:40]]

        # If an AI client is unavailable, fall back to the normal Browse search.
        if not client:
            return text

        # First ask the model to match against a compact representation of the
        # entire catalog.  Only names + searchable metadata are sent, avoiding
        # the old fixed 400-row limit and allowing seller-added products too.
        # For very large catalogs, process chunks and then make one final choice.
        all_items = catalog
        chunk_size = 100
        candidate_items = local_candidates[:]

        def ask_catalog(items):
            catalog_text = "\n".join(
                f"{i+1}. {item['name']} | craft={item['craft']} | category={item['category']} | material={item['material']} | state={item['state']} | district={item['district']}"
                for i, item in enumerate(items)
            )
            prompt = (
                "You are KAIVANNAM's multilingual product matching engine. "
                "The USER VOICE may be Tamil, English, Hindi, Malayalam, Telugu, Kannada, "
                "or mixed-language speech. It may contain pronunciation/phonetic spelling, "
                "a translated meaning, or only part of a product name. "
                "Choose ONLY from the catalog supplied below. "
                "If the user said a specific product, return the exact catalog product name. "
                "If the user said a generic category/craft/material/location, return a short "
                "catalog search term that Browse can use. "
                "If the user said a shared phrase such as 'Traditional Decor Piece', do not "
                "invent a product; return that phrase when it is present in product names. "
                "Never invent names. Return ONLY one final search string.\n\n"
                f"USER VOICE: {text}\n\nCATALOG:\n{catalog_text}"
            )
            try:
                response = client.chat.completions.create(
                    model="qwen/qwen3.8-27b",
                    reasoning_effort="none",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Match multilingual voice requests to the existing KAIVANNAM "
                                "catalog. Understand translation and phonetic pronunciation. "
                                "Never invent a catalog item. Return only one search string."
                            )
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0,
                    max_completion_tokens=80
                )
                value = (response.choices[0].message.content or "").strip().strip('"')
                # Remove accidental numbered/bulleted AI output before it can
                # reach Browse. Only the search phrase itself should remain.
                value = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", value)
                value = re.sub(r"\s+", " ", value).strip().strip('"')
                return value
            except Exception:
                return ""

        # For normal-sized catalogs, one call sees everything. For larger
        # seller catalogs, each chunk produces a possible match and a final
        # call chooses among only those real catalog candidates.
        if len(all_items) <= chunk_size:
            candidate = ask_catalog(all_items)
        else:
            candidates = []
            for i in range(0, len(all_items), chunk_size):
                result = ask_catalog(all_items[i:i + chunk_size])
                if result:
                    candidates.append(result)
            candidate = ""
            if candidates:
                unique_candidates = list(dict.fromkeys(candidates))
                if len(unique_candidates) == 1:
                    candidate = unique_candidates[0]
                else:
                    candidate = ask_catalog([
                        {"name": value, "craft": "", "category": "", "material": "", "state": "", "district": "", "region": "", "description": "", "artisan": ""}
                        for value in unique_candidates
                    ])

        if not candidate and candidate_items:
            candidate = ask_catalog(candidate_items)

        candidate_norm = _normalized_search_text(candidate)
        if candidate_norm:
            # Accept only a real product name or real catalog field.
            for item in catalog:
                for key in ("name", "craft", "category", "material", "state", "district", "region"):
                    value = _normalized_search_text(item[key])
                    if value and candidate_norm == value:
                        return item["name"] if key == "name" else candidate

            # Accept a shared product-name phrase only when it actually occurs
            # in the current catalog. Browse will then show all matching rows.
            if any(
                candidate_norm in _normalized_search_text(item["name"])
                for item in catalog
            ):
                return candidate

            # Existing canonical search vocabulary remains valid.
            canonical_terms = {
                "sari", "saree", "pot", "clay pot", "earthen pot", "pottery",
                "terracotta", "basket", "basketry", "bamboo", "cane", "mat",
                "painting", "toy", "doll", "jewellery", "jewelry", "leather",
                "wood craft", "wood carving", "bronze", "brass", "silk", "cotton",
                "textile", "handloom", "embroidery", "craft", "handmade", "handicraft"
            }
            if candidate_norm in {_normalized_search_text(x) for x in canonical_terms}:
                return candidate

        return text
    except Exception:
        # Never break the rest of the voice/Browse flow if catalog matching AI
        # is unavailable or a newly added product contains unusual text.
        return text


def voice_assistant():

    st.title(
        f"🎙️ {T('Voice Assistant')}"
    )

    st.markdown(
        f"""
        <div class="voice-panel">
            <h2 style="color:#6b2337">
            🎤 பேசுங்கள் — KAIVANNAM தேடட்டும்
            </h2>

            <p>
            Tamil, English, Hindi, Malayalam,
            Telugu or Kannada language-ல் பேசலாம்.
            </p>

            <p>
            Record button → பேசுங்கள் →
            Stop → text conversion →
            product search.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Voice can be spoken in any supported language. Auto Detect is the
    # default so the seller/customer does not have to choose the language
    # before speaking. A specific language can still be selected when needed.
    voice_languages = ["🌐 Auto Detect"] + LANGS
    lang = st.selectbox(
        T("Voice language"),
        voice_languages,
        index=0
    )

    language_codes = {
        "English": "en",
        "தமிழ்": "ta",
        "हिन्दी": "hi",
        "മലയാളം": "ml",
        "తెలుగు": "te",
        "ಕನ್ನಡ": "kn"
    }

    language_code = language_codes.get(lang)

    if hasattr(st, "audio_input"):

        audio = st.audio_input(
            f"🎤 {T('Record / Stop')}",
            sample_rate=16000,
            key="kaiv_voice_input"
        )

    else:

        audio = None

        st.error(
            "Update Streamlit using: "
            "pip install -U streamlit"
        )

    if audio is not None:

        client = ai_client()

        if client:

            with st.spinner(
                "🎧 Processing your voice..."
            ):

                try:
                    # Streamlit's audio_input returns the recorded WAV bytes.
                    # Passing a real file-like object with a filename makes
                    # the Groq transcription request more reliable.
                    audio_bytes = audio.getvalue()

                    audio_file = io.BytesIO(audio_bytes)
                    audio_file.name = "kaivannam_voice.wav"

                    # Do not send a Whisper prompt here. Groq limits the prompt
                    # to 896 characters, and a long catalog prompt can trigger
                    # invalid_prompt (400) before transcription even starts.
                    # Product/location matching is handled after transcription by
                    # the Browse search logic, so Whisper only needs to transcribe
                    # the user's actual speech.
                    # Keep this prompt intentionally short.  It is only a
                    # transcription instruction (never the product catalog),
                    # so spoken words are preserved instead of being guessed
                    # or replaced with stock phrases.
                    transcription_prompt = (
                        "Transcribe only the user's actual spoken words. "
                        "Do not invent, translate, summarize, or add words. "
                        "Keep names, places, and product words exactly as spoken."
                    )
                    if language_code == "ta":
                        transcription_prompt += " Keep Tamil words in Tamil script. Preserve English product, place, and craft words when spoken."
                    elif language_code:
                        transcription_prompt += " Preserve Indian product, place, and craft names exactly as spoken; mixed-language speech is allowed."
                    else:
                        transcription_prompt += " The speech may be English, Tamil, Hindi, Malayalam, Telugu, Kannada, or mixed-language. Detect the spoken language naturally and preserve product names."

                    transcription_kwargs = {
                        "file": audio_file,
                        "model": "whisper-large-v3",
                        "response_format": "json",
                        "temperature": 0,
                        "prompt": transcription_prompt
                    }
                    if language_code:
                        transcription_kwargs["language"] = language_code

                    result = client.audio.transcriptions.create(
                        **transcription_kwargs
                    )

                    recognized_text = (
                        getattr(
                            result,
                            "text",
                            ""
                        )
                        or ""
                    ).strip()

                    # Normalize common punctuation/spacing without changing the spoken words.
                    recognized_text = normalize_voice_query(recognized_text)
                    normalized_voice = recognized_text.lower().strip(" .,!?:;\"'“”‘’")

                    # Whisper sometimes hallucinates stock YouTube phrases on short/silent audio.
                    # Reject them even if extra punctuation/words were added around the phrase.
                    if (
                        any(phrase in normalized_voice for phrase in VOICE_HALLUCINATIONS)
                        or normalized_voice in VOICE_NOISE_PHRASES
                    ):
                        recognized_text = ""

                    if recognized_text:

                        # After Whisper transcription, resolve the spoken phrase
                        # against the actual catalog. This is what makes product
                        # names such as Tamil "புடவை / பானை / கூடை" and catalog
                        # names such as "Traditional Daka Piece" searchable even
                        # when the user speaks them in another supported language.
                        catalog_query = resolve_voice_to_catalog(
                            recognized_text,
                            client
                        )

                        st.session_state.voice_query = catalog_query

                        st.markdown(
                            f"""
                            <div class="voice-status">
                            ✅ <b>Recognized:</b>
                            {recognized_text}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        if catalog_query != recognized_text:
                            st.info(
                                f"🔎 Product matched: {catalog_query}"
                            )

                        st.success(
                            "Voice recognized. Opening product search..."
                        )

                        st.session_state.page = "Browse"

                        st.rerun()

                    else:

                        st.warning(
                            "Voice was not clear. Please try again."
                        )

                except Exception as e:

                    st.error(
                        f"Voice recognition failed: {e}"
                    )

        else:

            st.warning(
                "Add GROQ_API_KEY to "
                ".streamlit/secrets.toml "
                "to enable live voice recognition."
            )

    st.markdown(
        f"### ⌨️ {T('Type your request')}"
    )

    text = st.text_input(
        T("Type your request"),
        placeholder="தஞ்சாவூர் கைவினைப் பொருட்கள் காட்டு",
        key="voice_text_fallback"
    )

    if st.button(
        f"🔎 {T('Search Request')}",
        type="primary"
    ) and text.strip():

        st.session_state.voice_query = text.strip()

        st.session_state.page = "Browse"

        st.rerun()


# ============================================================
# PROFILE
# ============================================================

def profile():

    user = current_user()

    st.title(
        f"👤 {T('Profile')}"
    )

    st.write(
        f"**{T('Name')}:** {user['name']}"
    )

    st.write(
        f"**{T('User ID')}:** {user['user_id']}"
    )

    st.write(
        f"**{T('Role')}:** {user['role']}"
    )

    if user.get("email"):
        st.write(f"**Email:** {user['email']}")
    if user.get("phone"):
        st.write(f"**Phone:** {user['phone']}")
    if user.get("address"):
        st.write(f"**Address:** {user['address']}")

    current = (
        user.get("language")
        if user.get("language") in LANGS
        else "English"
    )

    language = st.selectbox(
        f"🌐 {T('Language')}",
        LANGS,
        index=LANGS.index(current)
    )

    if st.button(
        f"💾 {T('Save Language')}"
    ):

        exec_sql(
            """
            UPDATE users
            SET language=?
            WHERE user_id=?
            """,
            (
                language,
                user["user_id"]
            )
        )

        st.session_state.user = dictrow(
            one(
                """
                SELECT * FROM users
                WHERE user_id=?
                """,
                (
                    user["user_id"],
                )
            )
        )

        st.session_state.language = language

        st.success(
            "Language changed successfully."
        )

        st.rerun()


# ============================================================
# SELLER DASHBOARD
# ============================================================

def seller_dashboard():

    user = current_user()

    st.title(
        f"🧑‍🎨 {T('Seller Dashboard')}"
    )

    st.caption(
        f"{T('Welcome')}, {user['name']}"
    )

    products = q(
        """
        SELECT *
        FROM products
        WHERE artisan_user_id=?
        """,
        (
            user["user_id"],
        )
    )

    order_count = one(
        """
        SELECT COUNT(DISTINCT oi.order_id) n
        FROM order_items oi
        JOIN products p
        ON p.id=oi.product_id
        WHERE p.artisan_user_id=?
        """,
        (
            user["user_id"],
        )
    )["n"]

    revenue = one(
        """
        SELECT COALESCE(
            SUM(oi.quantity*oi.price),0
        ) n
        FROM order_items oi
        JOIN products p
        ON p.id=oi.product_id
        WHERE p.artisan_user_id=?
        """,
        (
            user["user_id"],
        )
    )["n"]

    wish = one(
        """
        SELECT COUNT(*) n
        FROM wishlist w
        JOIN products p
        ON p.id=w.product_id
        WHERE p.artisan_user_id=?
        """,
        (
            user["user_id"],
        )
    )["n"]

    rating = one(
        """
        SELECT COALESCE(AVG(r.rating),0) n
        FROM reviews r
        JOIN products p
        ON p.id=r.product_id
        WHERE p.artisan_user_id=?
        """,
        (
            user["user_id"],
        )
    )["n"]

    a, b, c, d = st.columns(4)

    a.metric(
        T("My Products"),
        len(products)
    )

    b.metric(
        T("Orders"),
        order_count
    )

    c.metric(
        T("Revenue"),
        f"₹{revenue:,.0f}"
    )

    d.metric(
        T("Wishlist"),
        wish
    )

    st.metric(
        T("Average Rating"),
        f"{rating:.1f}/5"
    )

    if products:

        df = pd.DataFrame([
            {
                "Product": r["name"][:28],
                "Price": r["price"],
                "Stock": r["stock"]
            }
            for r in products
        ])

        st.plotly_chart(
            px.bar(
                df,
                x="Product",
                y="Price",
                hover_data=["Stock"]
            ),
            width="stretch"
        )


# ============================================================
# SELLER PRODUCTS
# ============================================================

def seller_products():

    st.title(
        f"🧺 {T('My Products')}"
    )

    rows = q(
        """
        SELECT *
        FROM products
        WHERE artisan_user_id=?
        ORDER BY id DESC
        """,
        (
            current_user()["user_id"],
        )
    )

    if not rows:

        st.info(
            "No products yet."
        )

        return

    cols = st.columns(3)

    for i, r in enumerate(rows):

        with cols[i % 3]:

            product_card(
                r,
                "seller"
            )

            st.caption(
                f"{T('Stock')}: {r['stock']}"
            )

            if st.button(
                T("Remove"),
                key=f"sdel_{r['id']}"
            ):

                exec_sql(
                    """
                    DELETE FROM products
                    WHERE id=?
                    AND artisan_user_id=?
                    """,
                    (
                        r["id"],
                        current_user()["user_id"]
                    )
                )

                st.rerun()


# ============================================================
# ADD PRODUCT
# ============================================================

def add_product():

    # Apply AI-generated values before the widgets are created so Streamlit
    # displays the generated price and description immediately after upload.
    if st.session_state.get("add_product_apply_ai", False):
        ai_price_value = st.session_state.get("add_product_ai_price")
        try:
            if ai_price_value is not None and float(ai_price_value) > 0:
                st.session_state["add_product_price"] = float(ai_price_value)
        except (TypeError, ValueError):
            pass

        st.session_state["add_product_description"] = st.session_state.get(
            "add_product_ai_description", ""
        )
        st.session_state["add_product_apply_ai"] = False

    st.title(
        f"➕ {T('Add Product')}"
    )

    name = st.text_input(
        T("Product name")
    )

    craft = st.text_input(
        T("Craft type")
    )

    category = st.selectbox(
        T("Category"),
        [
            "Painting",
            "Textiles",
            "Pottery",
            "Wood Craft",
            "Metal Craft",
            "Jewellery",
            "Bamboo & Cane",
            "Embroidery",
            "Home Decor",
            "Toys",
            "Eco-friendly Crafts",
            "Stone Craft",
            "Leather Craft"
        ]
    )

    state = st.text_input(
        T("State")
    )

    district = st.text_input(
        "District / Region"
    )

    material = st.text_input(
        T("Material")
    )

    stored_price = st.session_state.get("add_product_price", 500.0)
    try:
        stored_price = float(stored_price) if stored_price is not None else 500.0
    except (TypeError, ValueError):
        stored_price = 500.0
    stored_price = max(1.0, min(100000.0, stored_price))

    price = st.number_input(
        "Price (₹)",
        1.0,
        100000.0,
        stored_price,
        step=100.0,
        key="add_product_price"
    )

    stock = st.number_input(
        T("Stock"),
        1,
        10000,
        10,
        key="add_product_stock"
    )

    description = st.text_area(
        T("Description"),
        value=st.session_state.get("add_product_ai_description", ""),
        key="add_product_description"
    )

    story = st.text_area(
        "Craft story",
        value=st.session_state.get("add_product_craft_story", "")
    )

    style = st.selectbox(
        T("Style"),
        [
            "Traditional",
            "Contemporary"
        ]
    )

    upload = st.file_uploader(
        "Product image (JPG, JPEG, PNG, WEBP)",
        type=[
            "png",
            "jpg",
            "jpeg",
            "webp"
        ],
        accept_multiple_files=False,
        help="On a phone, choose a photo from Gallery/Files. You can also use the camera option below to take a new product photo."
    )

    # Mobile sellers can take a product photo directly from the phone camera.
    # st.camera_input opens the device camera on supported mobile browsers and
    # returns the captured photo as an uploaded image, just like file_uploader.
    camera_upload = st.camera_input("📷 Take product photo with phone camera")
    upload_source = "gallery"
    if camera_upload is not None:
        upload = camera_upload
        upload_source = "camera"

    # IMPORTANT: Product image uploader is outside st.form so uploading an image
    # immediately reruns the app and triggers AI description + price generation.
    if upload:
        upload_bytes = upload.getvalue()
        upload_hash = hashlib.sha256(upload_bytes).hexdigest()[:16]
        upload_sig = f"{upload_source}:{upload.name}:{len(upload_bytes)}:{upload_hash}"
        language_changed = (
            st.session_state.get("add_product_ai_language") != current_lang()
        )
        if (
            st.session_state.get("add_product_upload_sig") != upload_sig
            or language_changed
        ):
            preview_path = None
            try:
                with st.spinner("AI is analyzing the product image and generating description & price..."):
                    ext = Path(upload.name).suffix.lower()
                    preview_path = APP_DIR / f".ai_preview_{current_user()['user_id']}_{upload_hash}{ext}"
                    preview_path.write_bytes(upload_bytes)

                    preview_relative_path = str(preview_path.relative_to(APP_DIR))
                    ai_price, ai_description = ai_product_image_price_and_description(
                        image_path=preview_relative_path,
                        name=name.strip(),
                        craft=craft.strip(),
                        category=category,
                        state=state.strip(),
                        district=district.strip(),
                        material=material.strip(),
                        fallback_price=price,
                        fallback_description=""
                    )

                    # Generate the craft story automatically from the SAME uploaded image.
                    ai_story = generate_craft_story_from_image_bytes(upload_bytes)

                    try:
                        st.session_state["add_product_ai_price"] = (
                            float(ai_price) if ai_price is not None and float(ai_price) > 0 else 0.0
                        )
                    except (TypeError, ValueError):
                        st.session_state["add_product_ai_price"] = 0.0
                    st.session_state["add_product_craft_story"] = ai_story or ""
                    st.session_state["add_product_ai_description"] = ai_description
                    st.session_state["add_product_upload_sig"] = upload_sig
                    st.session_state["add_product_ai_language"] = current_lang()
                    st.session_state["add_product_apply_ai"] = bool(ai_description or ai_price or ai_story)

                    if not ai_description or not ai_price or not ai_story:
                        st.warning(
                            "Live image AI did not return all requested fields. "
                            "No default/demo description, price, or story was inserted."
                        )
            finally:
                if preview_path and preview_path.exists():
                    try:
                        preview_path.unlink()
                    except Exception:
                        pass

            st.rerun()

    submit = st.button(
        T("Save Product"),
        type="primary"
    )

    if submit:

        if (
            not name.strip()
            or not craft.strip()
            or not state.strip()
        ):

            st.error(
                "Product name, craft type and state are required."
            )

            return

        image_path = ""

        if upload:

            ext = Path(
                upload.name
            ).suffix.lower()

            filename = (
                f"{current_user()['user_id']}_"
                f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                f"{ext}"
            )

            destination = (
                PRODUCT_DIR / filename
            )

            destination.write_bytes(
                upload_bytes if 'upload_bytes' in locals() else upload.getvalue()
            )

            image_path = str(
                destination.relative_to(
                    APP_DIR
                )
            )

        exec_sql(
            """
            INSERT INTO products(
                name,craft_type,category,
                state,district,region,
                material,description,
                price,stock,
                artisan,artisan_user_id,
                rating,review_count,
                style,image_key,image_path,
                cultural_significance
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                name,
                craft,
                category,
                state,
                district or "Local",
                district or "Local",
                material or "Handmade materials",
                description or "Handcrafted Indian product.",
                price,
                stock,
                current_user()["name"],
                current_user()["user_id"],
                0,
                0,
                style,
                keyify(craft),
                image_path,
                story
                or f"A handmade {craft} tradition from {state}."
            )
        )

        st.success(
            "Product added successfully."
        )


# ============================================================
# SELLER ORDERS
# ============================================================

def seller_orders():

    st.title(
        f"📦 {T('Seller Orders')}"
    )

    rows = q(
        """
        SELECT
            o.id order_id,
            o.status,
            o.created_at,
            o.payment_method,
            o.payment_status,
            o.shipping_name,
            o.shipping_phone,
            o.shipping_address,
            o.shipping_city,
            o.shipping_state,
            o.shipping_pincode,
            o.shipping_landmark,
            oi.quantity,
            oi.price,
            p.*
        FROM orders o
        JOIN order_items oi
        ON oi.order_id=o.id
        JOIN products p
        ON p.id=oi.product_id
        WHERE p.artisan_user_id=?
        ORDER BY o.id DESC
        """,
        (
            current_user()["user_id"],
        )
    )

    if not rows:

        st.info(
            "No seller orders yet."
        )

        return

    for r in rows:

        r = dictrow(r)

        st.image(
            str(
                product_image(r)
            ),
            width=120
        )

        st.write(
            f"**Order #{r['order_id']}** — "
            f"{r['name']} × "
            f"{r['quantity']} — "
            f"₹{r['price'] * r['quantity']:,.0f}"
        )

        st.markdown("**📦 Customer Delivery Details**")
        st.write(
            f"**{r.get('shipping_name') or 'Customer'}**  \n"
            f"📞 {r.get('shipping_phone') or '-'}  \n"
            f"📍 {r.get('shipping_address') or '-'}, {r.get('shipping_city') or '-'}, "
            f"{r.get('shipping_state') or '-'} - {r.get('shipping_pincode') or '-'}"
        )
        if r.get("shipping_landmark"):
            st.caption(f"Landmark: {r['shipping_landmark']}")
        st.caption(
            f"Payment: {r.get('payment_method') or '-'} • {r.get('payment_status') or '-'}"
        )

        current_status = (
            STATUSES.index(
                r["status"]
            )
            if r["status"] in STATUSES
            else 0
        )

        new_status = st.selectbox(
            T("Update status"),
            STATUSES,
            index=current_status,
            key=f"os_{r['order_id']}_{r['id']}"
        )

        if st.button(
            T("Save status"),
            key=f"oss_{r['order_id']}_{r['id']}"
        ):

            exec_sql(
                """
                UPDATE orders
                SET status=?
                WHERE id=?
                """,
                (
                    new_status,
                    r["order_id"]
                )
            )

            exec_sql(
                """
                INSERT INTO delivery_tracking
                (order_id,status,event_time)
                VALUES(?,?,?)
                """,
                (
                    r["order_id"],
                    new_status,
                    datetime.now().isoformat()
                )
            )

            st.success(
                "Status saved."
            )


# ============================================================
# RETURNS & REFUNDS
# ============================================================

def returns_policy():

    user = current_user()
    st.title("↩️ Returns & Refunds")

    st.markdown(
        """
        **KAIVANNAM Return Policy**

        - Return requests can be raised within **7 days of delivery**.
        - The item should be unused and returned in the condition in which it was received,
          except when it arrived damaged, defective, or incorrect.
        - For a damaged, defective, or wrong item, upload/describe the issue in the return request.
        - Refunds are processed after the seller/admin accepts the return according to the payment method.
        - Cash-on-Delivery orders are marked for refund processing separately; no cash is collected from the seller as a refund.
        """
    )

    if user["role"] == "Customer":
        requests = q(
            """
            SELECT rr.*, oi.product_id, oi.quantity, oi.price, p.name, o.status AS order_status
            FROM return_requests rr
            JOIN order_items oi ON oi.id=rr.order_item_id
            JOIN orders o ON o.id=rr.order_id
            JOIN products p ON p.id=oi.product_id
            WHERE rr.user_id=?
            ORDER BY rr.id DESC
            """,
            (user["user_id"],)
        )

        if requests:
            st.subheader("My Return Requests")
            for rr in requests:
                st.write(
                    f"**Order #{rr['order_id']} — {rr['name']}** • "
                    f"Return: **{rr['status']}** • Refund: **{rr['refund_status']}**"
                )
                st.caption(f"Reason: {rr['reason']}")

    else:
        requests = q(
            """
            SELECT rr.*, oi.product_id, oi.quantity, oi.price, p.name,
                   o.shipping_name, o.shipping_phone, o.shipping_city,
                   o.shipping_state, o.shipping_pincode
            FROM return_requests rr
            JOIN order_items oi ON oi.id=rr.order_item_id
            JOIN orders o ON o.id=rr.order_id
            JOIN products p ON p.id=oi.product_id
            WHERE p.artisan_user_id=?
            ORDER BY rr.id DESC
            """,
            (user["user_id"],)
        )
        st.subheader("Seller Return Requests")
        if not requests:
            st.info("No return requests yet.")
        for rr in requests:
            st.write(f"**Order #{rr['order_id']} — {rr['name']} × {rr['quantity']}**")
            st.caption(f"Customer: {rr['shipping_name'] or '-'} • {rr['shipping_phone'] or '-'}")
            st.caption(f"Reason: {rr['reason']}")
            c1, c2 = st.columns(2)
            status = c1.selectbox(
                "Return status",
                ["Requested", "Approved", "Rejected", "Received", "Completed"],
                index=["Requested", "Approved", "Rejected", "Received", "Completed"].index(rr['status'])
                if rr['status'] in ["Requested", "Approved", "Rejected", "Received", "Completed"] else 0,
                key=f"return_status_{rr['id']}"
            )
            refund = c2.selectbox(
                "Refund status",
                ["Pending", "Processing", "Refunded", "Not Applicable"],
                index=["Pending", "Processing", "Refunded", "Not Applicable"].index(rr['refund_status'])
                if rr['refund_status'] in ["Pending", "Processing", "Refunded", "Not Applicable"] else 0,
                key=f"refund_status_{rr['id']}"
            )
            if st.button("Save return update", key=f"save_return_{rr['id']}"):
                exec_sql(
                    "UPDATE return_requests SET status=?,refund_status=?,updated_at=? WHERE id=?",
                    (status, refund, datetime.now().isoformat(), rr['id'])
                )
                st.success("Return request updated.")
                st.rerun()


# ============================================================
# PHOTO RESCUE
# ============================================================

def photo_rescue():

    st.title(
        f"📸 {T('AI Photo Rescue')}"
    )

    upload = st.file_uploader(
        T("Upload a product photo"),
        type=[
            "png",
            "jpg",
            "jpeg",
            "webp"
        ]
    )

    if upload:

        image = Image.open(
            upload
        ).convert("RGB")

        enhanced = ImageEnhance.Contrast(
            image
        ).enhance(1.12)

        enhanced = ImageEnhance.Sharpness(
            enhanced
        ).enhance(1.35)

        a, b = st.columns(2)

        a.image(
            image,
            caption=T("Before"),
            width="stretch"
        )

        b.image(
            enhanced,
            caption=T("After"),
            width="stretch"
        )

        st.info(
            "Local Pillow enhancement completed."
        )


# ============================================================
# WASTE TO CRAFT
# ============================================================

def waste_craft():

    st.title(
        f"♻️ {T('Waste → Craft AI')}"
    )

    material = st.text_area(
        T("Leftover material"),
        placeholder="Bamboo pieces + fabric scraps"
    )

    if st.button(
        T("Suggest Craft Ideas")
    ) and material.strip():

        result = ai_call(
            f"""
            Suggest 5 practical Indian handicraft
            products using this leftover material:

            {material}

            Include:
            process,
            target customers,
            approximate value,
            sustainability benefit.

            Language:
            {current_lang()}
            """
        )

        if result:

            st.write(result)

        else:

            st.info(
                "AI Demo Mode"
            )

            ideas = [
                "Utility basket",
                "Decorative wall panel",
                "Desk organiser",
                "Plant holder",
                "Gift item"
            ]

            for idea in ideas:

                st.markdown(
                    f"**{idea}** — "
                    "Reuse available material with minimal waste."
                )


# ============================================================
# MATERIAL EXCHANGE
# ============================================================

def material_exchange():

    st.title(
        f"🔄 {T('Material Exchange')}"
    )

    a, b = st.tabs([
        T("List Material"),
        T("Browse & Request")
    ])

    with a:

        with st.form(
            "material_form"
        ):

            material = st.text_input(
                T("Material offered")
            )

            quantity = st.text_input(
                T("Quantity")
            )

            location = st.text_input(
                T("Location")
            )

            wanted = st.text_input(
                T("Wanted material")
            )

            description = st.text_area(
                T("Description")
            )

            if st.form_submit_button(
                T("Publish")
            ):

                if material.strip() and wanted.strip():

                    exec_sql(
                        """
                        INSERT INTO material_listings
                        (
                        user_id,material,
                        quantity,location,
                        wanted,description
                        )
                        VALUES(?,?,?,?,?,?)
                        """,
                        (
                            current_user()["user_id"],
                            material,
                            quantity,
                            location,
                            wanted,
                            description
                        )
                    )

                    st.success(
                        "Material listed successfully."
                    )

    with b:

        rows = q(
            """
            SELECT m.*,u.name
            FROM material_listings m
            JOIN users u
            ON u.user_id=m.user_id
            ORDER BY m.id DESC
            """
        )

        for row in rows:

            st.markdown(
                f"""
                <div class="skill-card">
                    <h3>
                    {row['material']}
                    </h3>

                    <b>
                    {row['quantity']}
                    </b>

                    <p>
                    Artisan: {row['name']}
                    </p>

                    <p>
                    Location: {row['location']}
                    </p>

                    <p>
                    Wants: {row['wanted']}
                    </p>

                    <p>
                    {row['description']}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

            if (
                row["user_id"]
                != current_user()["user_id"]
            ):

                if st.button(
                    T("Send Exchange Request"),
                    key=f"br_{row['id']}"
                ):

                    exec_sql(
                        """
                        INSERT INTO barter_requests
                        (from_user,to_user,
                         material,offer)
                        VALUES(?,?,?,?)
                        """,
                        (
                            current_user()["user_id"],
                            row["user_id"],
                            row["wanted"],
                            row["material"]
                        )
                    )

                    st.success(
                        "Exchange request sent."
                    )


# ============================================================
# SKILL EXCHANGE
# ============================================================

def skill_exchange():

    st.title(
        f"🤝 {T('Skill Exchange')}"
    )

    st.markdown(
        f"""
        <div class="hero">
            <h1>🤝 {T("Skill Exchange Hub")}</h1>
            <p>
            Share your traditional craft skills,
            learn from another artisan and build
            a collaborative artisan network.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # CREATE SKILL OFFER
    with st.form(
        "skill_form"
    ):

        st.subheader(
            "➕ "
            + T("Offer Skill")
        )

        skill = st.text_input(
            T("Skill offered"),
            placeholder=(
                "Example: Thanjavur painting"
            )
        )

        wanted_skill = st.text_input(
            T("Skill wanted"),
            placeholder=(
                "Example: Social media marketing"
            )
        )

        submit = st.form_submit_button(
            T("Offer Skill"),
            type="primary"
        )

    if submit:

        if (
            skill.strip()
            and wanted_skill.strip()
        ):

            exec_sql(
                """
                INSERT INTO skill_exchange
                (
                    from_user,
                    skill,
                    wanted_skill,
                    status
                )
                VALUES(?,?,?,'Open')
                """,
                (
                    current_user()["user_id"],
                    skill.strip(),
                    wanted_skill.strip()
                )
            )

            st.success(
                T(
                    "Skill exchange posted successfully."
                )
                if current_lang() == "தமிழ்"
                else "Skill exchange posted successfully."
            )

            st.rerun()

    st.divider()

    # AVAILABLE SKILLS
    st.subheader(
        "🌐 Available Skill Exchanges"
    )

    rows = q(
        """
        SELECT
            s.*,
            u.name,
            u.role
        FROM skill_exchange s
        JOIN users u
        ON u.user_id=s.from_user
        WHERE s.from_user<>?
        ORDER BY s.id DESC
        """,
        (
            current_user()["user_id"],
        )
    )

    if not rows:

        st.info(
            "No skill exchanges available yet."
        )

    for row in rows:

        st.markdown(
            f"""
            <div class="skill-card">

                <h3>
                    🧑‍🎨 {row['name']}
                </h3>

                <p>
                    <b>{T("Role")}:</b>
                    {row['role']}
                </p>

                <p>
                    🎁 <b>{T("Skill offered")}:</b>
                    {row['skill']}
                </p>

                <p>
                    🔎 <b>{T("Skill wanted")}:</b>
                    {row['wanted_skill']}
                </p>

                <p>
                    📌 <b>Status:</b>
                    {row['status']}
                </p>

            </div>
            """,
            unsafe_allow_html=True
        )

        if row["status"] == "Open":

            if st.button(
                f"🤝 {T('Connect')}",
                key=f"skill_connect_{row['id']}"
            ):

                exec_sql(
                    """
                    UPDATE skill_exchange
                    SET
                        to_user=?,
                        status='Requested'
                    WHERE id=?
                    """,
                    (
                        current_user()["user_id"],
                        row["id"]
                    )
                )

                st.success(
                    "Skill exchange request sent."
                )

                st.rerun()

    # MY POSTS
    st.divider()

    st.subheader(
        "📋 My Skill Exchanges"
    )

    mine = q(
        """
        SELECT *
        FROM skill_exchange
        WHERE from_user=?
           OR to_user=?
        ORDER BY id DESC
        """,
        (
            current_user()["user_id"],
            current_user()["user_id"]
        )
    )

    if not mine:

        st.caption(
            "You have not created or requested a skill exchange yet."
        )

    for row in mine:

        st.write(
            f"🎨 **{row['skill']}** "
            f"↔ "
            f"🔎 **{row['wanted_skill']}** "
            f"— **{row['status']}**"
        )


# ============================================================
# SIDEBAR
# ============================================================

def sidebar():

    user = current_user()

    # Make sure current language exists
    if user.get("language") in LANGS:
        st.session_state.language = user["language"]

    sidebar_logo = LOGO_DIR / "logo.png"

    if sidebar_logo.exists():

        st.sidebar.image(
            str(sidebar_logo),
            width=150
        )

    st.sidebar.markdown(
        "## கைவண்ணம்"
    )

    st.sidebar.caption(
        "KAIVANNAM • Indian Artisan Marketplace"
    )

    # --------------------------------------------------------
    # GLOBAL LANGUAGE SWITCH
    # --------------------------------------------------------

    selected_language = st.sidebar.selectbox(
        "🌐 Language / மொழி",
        LANGS,
        index=LANGS.index(
            current_lang()
        ),
        key="global_language"
    )

    if selected_language != current_lang():

        st.session_state.language = selected_language

        exec_sql(
            """
            UPDATE users
            SET language=?
            WHERE user_id=?
            """,
            (
                selected_language,
                user["user_id"]
            )
        )

        st.session_state.user = dictrow(
            one(
                """
                SELECT *
                FROM users
                WHERE user_id=?
                """,
                (
                    user["user_id"],
                )
            )
        )

        st.rerun()

    st.sidebar.divider()

    # --------------------------------------------------------
    # CUSTOMER MENU
    # --------------------------------------------------------

    if user["role"] == "Customer":

        pairs = [
            ("Home", T("Home")),
            ("Browse", T("Browse")),
            ("Product Details", T("Product Details")),
            ("Wishlist", T("Wishlist")),
            ("Cart", T("Cart")),
            ("Checkout", T("Checkout")),
            ("Orders", T("Orders")),
            ("Returns & Refunds", "Returns & Refunds"),
            ("Heritage Map", T("Heritage Map")),
            ("AI Shopping Assistant", T("AI Shopping Assistant")),
            ("Voice Assistant", T("Voice Assistant")),
            ("Profile", T("Profile"))
        ]

    # --------------------------------------------------------
    # SELLER MENU
    # --------------------------------------------------------

    else:

        pairs = [
            ("Seller Dashboard", T("Seller Dashboard")),
            ("My Products", T("My Products")),
            ("Add Product", T("Add Product")),
            ("Seller Orders", T("Seller Orders")),
            ("Returns & Refunds", "Returns & Refunds"),
            ("AI Photo Rescue", T("AI Photo Rescue")),
            ("Waste → Craft AI", T("Waste → Craft AI")),
            ("Craft Stories", T("Craft Stories")),
            ("Heritage Map", T("Heritage Map")),
            ("Voice Assistant", T("Voice Assistant")),
            ("Material Exchange", T("Material Exchange")),
            ("Skill Exchange", T("Skill Exchange")),
            ("Profile", T("Profile"))
        ]

    shown = [
        item[1]
        for item in pairs
    ]

    current_page = st.session_state.get(
        "page",
        pairs[0][0]
    )

    index = next(
        (
            i
            for i, pair in enumerate(pairs)
            if pair[0] == current_page
        ),
        0
    )

    choice = st.sidebar.radio(
        T("Navigate"),
        shown,
        index=index
    )

    selected_pair = pairs[
        shown.index(choice)
    ]

    st.session_state.page = selected_pair[0]

    st.sidebar.divider()

    st.sidebar.write(
        f"👤 {user['name']}"
    )

    st.sidebar.write(
        f"{T('Role')}: {user['role']}"
    )

    if st.sidebar.button(
        T("Logout")
    ):

        st.session_state.clear()
        try:
            st.query_params.clear()
        except Exception:
            pass
        st.rerun()

    if ai_client():

        st.sidebar.success(
            "🟢 Live AI"
        )

    else:

        st.sidebar.warning(
            "🟡 AI Demo Mode"
        )

    st.sidebar.caption(
        "Payments: Demo Mode • SQLite persistent data"
    )


# ============================================================
# MAIN ROUTER
# ============================================================

def main():

    # Reuse the last logged-in account when the app is opened again.
    restore_saved_login()

    if "user" not in st.session_state:

        login_page()
        return

    sidebar()

    page = st.session_state.get(
        "page",
        "Home"
    )

    funcs = {

        "Home": home,

        "Browse": browse,

        "Product Details":
            product_details,

        "Wishlist":
            wishlist,

        "Cart":
            cart_page,

        "Checkout":
            checkout_page,

        "Orders":
            orders,

        "Returns & Refunds":
            returns_policy,

        "Heritage Map":
            heritage_map,

        "AI Shopping Assistant":
            ai_shopping,

        "Voice Assistant":
            voice_assistant,

        "Profile":
            profile,

        "Seller Dashboard":
            seller_dashboard,

        "My Products":
            seller_products,

        "Add Product":
            add_product,

        "Seller Orders":
            seller_orders,

        "AI Photo Rescue":
            photo_rescue,

        "Waste → Craft AI":
            waste_craft,

        "Material Exchange":
            material_exchange,

        "Skill Exchange":
            skill_exchange
    }

    funcs.get(
        page,
        home
    )()


# ============================================================
# RUN
# ============================================================

main()
