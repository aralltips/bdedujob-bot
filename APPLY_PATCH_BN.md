# BDEduJob Auto-Publish Queue — প্রয়োগের নির্দেশনা

এই patch-এ ৫টি যাচাইকৃত পোস্টের HTML, queue manifest, Blogger/Facebook publish helper এবং বিদ্যমান GitHub Actions workflow-এর আপডেট আছে। **কোনো secret/token প্যাকেটে নেই।**

## একবারের GitHub আপলোড

1. ZIP extract করুন। ফাইলগুলো `aralltips/bdedujob-bot` repository-র root-এ একই path-এ রাখুন।
2. `.github/workflows/auto_post.yml`-টি repository-র একই ফাইল দিয়ে replace করুন। নতুন ফাইলগুলো root ও `verified_posts/`-এ রাখুন।
3. সব পরিবর্তন **একটি commit-এ** save করুন। এই workflow-তে push-trigger বন্ধ রাখা হয়েছে; তাই একাধিক ফাইল upload করার সময় দ্রুত ধারাবাহিক post হবে না।
4. বিদ্যমান Actions secrets অপরিবর্তিত রাখুন: `BLOGGER_CLIENT_ID`, `BLOGGER_CLIENT_SECRET`, `BLOGGER_REFRESH_TOKEN`, `FB_PAGE_ACCESS_TOKEN`। এগুলো chat-এ পাঠাবেন না।
5. Commit-এর পর workflow-এর পরবর্তী scheduled run (`12,42 * * * *` UTC; Dhaka-তেও প্রতি ঘণ্টায় :12 ও :42 মিনিটে) queue থেকে **একটি** eligible post publish করবে। এরপর পরের queue item পরবর্তী run-এ যাবে।

## Queue-এর প্রকাশ-ক্রম

1. HSC ২০২৬ পুনঃনিরীক্ষণ — ৭ নভেম্বরের পরে স্বয়ংক্রিয়ভাবে বাদ যাবে
2. CAG — ২৫ নভেম্বরের পরে বাদ যাবে
3. DGMS — ২১ নভেম্বরের পরে বাদ যাবে
4. ঢাকা বিশ্ববিদ্যালয়ের job roundup — ১৫ নভেম্বরের প্রথম deadline-এর আগে publish না হলে বাদ যাবে
5. ঢাকা বোর্ড SSC বৃত্তি তালিকা

প্রতিটি run-এ public Blogger feed-এ title duplicate কিনা যাচাই হয়; `posted_jobs.json`-এ idempotency marker রাখা হয়; শেষ post/attempt-এর ৩০ মিনিটের মধ্যে নতুন publish slot নেওয়া হয় না। Queue item publish হলে বিদ্যমান Facebook helper দিয়ে custom banner + URL-হীন caption এবং প্রথম comment-এ Blogger URL শেয়ারের চেষ্টা করবে।

## গুরুত্বপূর্ণ যাচাই

- Local `--dry-run` পরীক্ষা সফল: পরবর্তী candidate HSC ২০২৬ পুনঃনিরীক্ষণ পোস্ট দেখিয়েছে; কোনো live publish করা হয়নি।
- Blogger/GitHub-এ এই patch এখান থেকে push বা workflow trigger করা যাচ্ছে না; repository owner-কে একবার commit করতে হবে।
- Actions run “success” হলেই live post হয়েছে ধরে নেবেন না—Blogger feed-এ post title/date এবং Facebook Page-এ photo + first comment মিলিয়ে দেখুন। OAuth secret অকার্যকর হলে workflow log-এ publish error থাকবে; token chat-এ দেবেন না।
- dlvr.it OFF-ই রাখুন; নতুন queue publisher Facebook Page-এ সরাসরি photo/caption/first-comment পদ্ধতি ব্যবহার করে।

## Patch-এর ফাইলসমূহ

- `.github/workflows/auto_post.yml` — প্রতি ৩০ মিনিটে queue-first workflow, এক run-এ সর্বোচ্চ একটি post
- `publish_verified_post_queue.py` — duplicate, deadline, cooldown যাচাইসহ publish helper
- `verified_post_queue.json` — ক্রম, labels, banner URL, Facebook caption ও active-until metadata
- `verified_posts/*.html` — পাঁচটি Blogger-ready post body
- `verified_post_state.json` — প্রথমবারের খালি state; workflow নিজে আপডেট করবে
