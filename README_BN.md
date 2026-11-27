# BDEduJob — লিংক-ভিত্তিক সরাসরি প্রকাশ সেটআপ (Google Drive → GitHub → Blogger + Facebook)

এই সেটআপ একবার বসালে আপনি শুধু চ্যাটে **যেকোনো চাকরির/শিক্ষার লিংক দেবেন**, আমি আপনার স্টাইলে লেখা, ব্যানার ও মূল প্রকাশের তারিখ (`published_iso`) সরাসরি আপনার Google Drive-এর কিউ ফাইলে সেভ করে দেব—আর GitHub বট সেটি স্বয়ংক্রিয়ভাবে Blogger ও Facebook Page-এ প্রকাশ করবে।

---

## আগে থেকেই যা সেট করা হয়েছে
- আপনার Google Drive-এ **`BDEduJob_Direct_Publish_Queue.json`** তৈরি করা হয়েছে (`File ID: 1DMGaDPWncdRpjH53SJGnEHkYCoEV376O`)।
- এতে কেবল পাবলিক ব্লগ পোস্টের ড্রাফট রাখা হবে—কোনো token বা secret এতে থাকবে না।

---

## আপনার একবারের সেটআপ (২টি ছোট কাজ)

### ১. GitHub-এ এই ৩টি ফাইল আপলোড করুন (`aralltips/bdedujob-bot`)
1. `auto_job_blogger.py` → রিপোজিটরির **root**-এ replace করুন।
2. `publish_verified_post_queue.py` → রিপোজিটরির **root**-এ replace করুন।
3. `.github/workflows/auto_post.yml` → রিপোজিটরির **`.github/workflows/`** ফোল্ডারে replace করুন।

*(নোট: নতুন `auto_post.yml`-এ `ENABLE_AUTO_SCRAPER: "false"` রাখা হয়েছে, যাতে শুধু আপনার দেওয়া লিংক থেকেই পোস্ট প্রকাশ হয়। পুরনো অটো-স্ক্র্যাপারও চালু রাখতে চাইলে কেবল ওই লাইনটি `"true"` করে দেবেন।)*

### ২. Blogger OAuth টোকেন ঠিক করুন (যাতে ৭ দিনে আর বন্ধ না হয়)
1. Google Cloud Console → **OAuth consent screen / Audience** → অ্যাপটি **In production** (`Publish App`) করুন।
2. **OAuth 2.0 Playground**-এ আপনার `Client ID` ও `Client Secret` দিয়ে `https://www.googleapis.com/auth/blogger` স্কোপে নতুন `Refresh Token` নিন।
3. GitHub `aralltips/bdedujob-bot` → **Settings → Secrets and variables → Actions** → **`BLOGGER_REFRESH_TOKEN`** আপডেট করুন।

---

## প্রতিদিন কীভাবে কাজ করবে?
1. আপনি চ্যাটে যেকোনো নতুন সার্কুলার বা নোটিশের **লিংক** দেবেন।
2. আমি অফিসিয়াল সোর্স যাচাই করে আপনার স্টাইলে HTML, ব্যানার, Labels, Facebook ক্যাপশন এবং **মূল প্রকাশের তারিখ (`published_iso`)** সহ সরাসরি Google Drive-এর `BDEduJob_Direct_Publish_Queue.json`-এ যোগ করব।
3. GitHub বট প্রতি **৩০ মিনিটে (`:12` ও `:42`)** অটোমেটিক কিউ থেকে পোস্ট প্রকাশ করবে—অথবা আপনি চাইলে GitHub **Actions → Run workflow** ক্লিক করলেই এক সাথে **১০টি পর্যন্ত** কিউ করা পোস্ট মুহূর্তেই লাইভ (Blogger + Facebook) হয়ে যাবে।
