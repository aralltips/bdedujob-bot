# BD Education & Job Info (`bdedujob.blogspot.com`) — অটোমেটিক জব সার্কুলার বট ও Google AdSense গাইড

এই প্রজেক্টটি বাংলাদেশের জনপ্রিয় সরকারি ও বেসরকারি জব পোর্টাল থেকে নতুন জব সার্কুলার সংগ্রহ করে, **স্বয়ংক্রিয়ভাবে বাংলা থাম্বনেইল ব্যানার ছবি ডিজাইন করে** এবং আপনার সাইটের হুবহু স্টাইলে **১০০% অন-পেজ SEO ও AdSense-উপযোগী পোস্ট** লিখে সরাসরি আপনার ব্লগারে পাবলিশ করবে।

---

## ধাপ ১: আপনার সাইটে Google AdSense পাওয়ার জন্য জরুরি ৫টি সংশোধন (১৫ মিনিটের কাজ)

আপনার `bdedujob.blogspot.com` সাইটটি স্ক্যান করে দেখা গেছে এতে **২২০টি পোস্ট** এবং জরুরি পেজগুলো (`About Us`, `Contact Us`, `Privacy Policy`, `Disclaimer`) রয়েছে। তবে AdSense-এ আবেদন করার আগে নিচের ৫টি সমস্যা অবশ্যই ঠিক করে নিন:

১. **Adsterra / Pop-under ও Direct Link বিজ্ঞাপন কোড সরান (সবচেয়ে জরুরি):**
   - আপনার থিমের HTML-এ বর্তমানে `//contemplatethwartcooperation.com/...` এবং `foremedia.net` এর পপ-আন্ডার/থার্ড-পার্টি অ্যাড স্ক্রিপ্ট রয়েছে। Blogger Dashboard ➔ **Theme** ➔ **Edit HTML**-এ গিয়ে এই স্ক্রিপ্টগুলো মুছে ফেলুন।
   - পুরনো কিছু পোস্টের ছবিতে ও বাটনে `highcpmgate.com` (Adsterra Direct Link) দেওয়া আছে—সেগুলো সরিয়ে ফেলুন।

২. **`ads.txt` ও Publisher ID-র গরমিল ঠিক করুন:**
   - আপনার সাইটের থিমে রয়েছে `ca-pub-4805266758689935`, কিন্তু `bdedujob.blogspot.com/ads.txt`-এ দেওয়া আছে `google.com, pub-1979853277701463, DIRECT, f08c47fec0942fa` (শেষের `0` অক্ষরটিও কাটা পড়েছে)।
   - **সমাধান:** Blogger ➔ **Settings** ➔ **Monetization** ➔ **Custom ads.txt**-এ আপনার প্রকৃত AdSense Publisher ID দিয়ে নিচের ফরম্যাটে বসান:
     `google.com, pub-আপনার_আইডি, DIRECT, f08c47fec0942fa0`

৩. **ভাঙা RSS Feed Redirect (`rss.app`) মুছে দিন:**
   - Blogger ➔ **Settings** ➔ **Site feed** ➔ **Post Feed Redirect URL**-এ থাকা `https://rss.app/feeds/IxfTAyq0ymTmXDXb.xml` লিংকটি মুছে সম্পূর্ণ ফাঁকা (Blank) করে Save করুন।

৪. **Contact Us পেজের বাড়তি লেখাটি মুছুন:**
   - আপনার `Contact Us` পেজের ভেতরে লেখা আছে: `(Blogger Layout > Add Gadget > Contact Form)`। পেজটি Edit করে ব্র্যাকেটের এই লেখাটি মুছে দিন।

৫. **অটোমেশন বট চালু করে নতুন ১৫-২০টি পোস্ট পাবলিশ হতে দিন:**
   - আপনার সাইটে শেষ পোস্ট হয়েছিল ২৮ অক্টোবর ২০২৪ সালে। AdSense-এ আবেদনের আগে এই অটোমেশন স্ক্রিপ্টটি চালু করে অন্তত ৭-১০ দিন নতুন (২০২৬ সালের) পোস্ট পাবলিশ হতে দিন।

---

## ধাপ ২: অটোমেশন স্ক্রিপ্টটি চালু করার নিয়ম (GitHub Actions - ১০০% ফ্রি)

### প্রয়োজনীয় API Key সংগ্রহ:
1. **Blogger Blog ID:** আপনার ব্লগার ড্যাশবোর্ডে ঢুকলে ব্রাউজারের লিংকে `blogs/` এর পরে যে ১৯ সংখ্যার নম্বরটি থাকে সেটিই আপনার `BLOGGER_BLOG_ID`।
2. **Google Cloud OAuth2 (`BLOGGER_CLIENT_ID`, `BLOGGER_CLIENT_SECRET`, `BLOGGER_REFRESH_TOKEN`):**
   - [Google Cloud Console](https://console.cloud.google.com/)-এ একটি প্রজেক্ট খুলে **Blogger API v3** Enable করুন।
   - **Credentials** থেকে OAuth Client ID তৈরি করুন এবং [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/) ব্যবহার করে `https://www.googleapis.com/auth/blogger` স্কোপ সিলেক্ট করে `Refresh Token` নিন।
3. **Google Gemini API Key (`GEMINI_API_KEY` - ফ্রি):**
   - [Google AI Studio](https://aistudio.google.com/app/apikey) থেকে ফ্রি API Key নিন (এটি প্রতিটি সার্কুলারকে ১০০% ইউনিক ও AdSense-বান্ধব ভাষায় সাজিয়ে লিখবে)।
4. **ImgBB API Key (`IMGBB_API_KEY` - ফ্রি):**
   - [api.imgbb.com](https://api.imgbb.com/) থেকে ফ্রি API Key নিন (অটোমেটিক ডিজাইন করা ব্যানার ছবি হোস্ট করার জন্য)।

### GitHub-এ সেটআপ:
1. আপনার GitHub একাউন্টে একটি নতুন Repository তৈরি করে এই ফোল্ডারের সব ফাইল আপলোড করুন।
2. Repository-র **Settings ➔ Secrets and variables ➔ Actions**-এ গিয়ে উপরের ৬টি Secret (`BLOGGER_BLOG_ID`, `BLOGGER_CLIENT_ID`, `BLOGGER_CLIENT_SECRET`, `BLOGGER_REFRESH_TOKEN`, `GEMINI_API_KEY`, `IMGBB_API_KEY`) যুক্ত করুন।
3. ব্যস! প্রতি ৪ ঘণ্টা পর পর স্ক্রিপ্টটি অটোমেটিক নতুন জব সার্কুলার চেক করবে, ব্যানার ডিজাইন করবে এবং আপনার ব্লগে পাবলিশ করে দেবে।
   - আপনি যদি শুরুতে **Draft** হিসেবে রাখতে চান, তবে `.github/workflows/auto_post.yml` ফাইলে `BLOGGER_IS_DRAFT: "true"` করে দিন। আর সরাসরি পাবলিশ করতে চাইলে `"false"` রাখুন।
