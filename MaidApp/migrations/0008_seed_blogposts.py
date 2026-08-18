from django.db import migrations
from django.utils import timezone
from datetime import datetime


def make_dt(date_str):
    """Return an aware datetime from 'YYYY-MM-DD'."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return timezone.make_aware(dt)


POSTS = [
    {
        "slug": "10-things-check-before-hiring-house-maid-nigeria",
        "title": "10 Things You Must Check Before Hiring a House Maid in Nigeria",
        "excerpt": (
            "Hiring domestic help in Nigeria requires more than a phone interview. "
            "From NIN verification to reference checks, here's a complete checklist "
            "every employer should follow before bringing someone into their home."
        ),
        "category": "hiring",
        "author_name": "Adaeze Okafor",
        "author_avatar": "https://randomuser.me/api/portraits/women/44.jpg",
        "author_bio": (
            "Adaeze writes about domestic employment, household management, and career "
            "development for domestic professionals across Nigeria. She has over 8 years "
            "of experience covering the Nigerian labour market."
        ),
        "cover_image": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=1200&q=80",
        "content": (
            "<p>Hiring someone to work inside your home is one of the most personal decisions "
            "you'll make. Unlike hiring for a corporate role, the domestic hire lives and works "
            "in your private space — around your children, your property, and your daily routines.</p>"
            "<h2>1. Verify Their NIN (National Identity Number)</h2>"
            "<p>The National Identification Number is the most basic form of identity verification "
            "available in Nigeria. Every Nigerian adult should have one. Before you do anything else, "
            "ask for the candidate's NIN and verify it through the NIMC MobileID app.</p>"
            "<h2>2. Run a Background Check</h2>"
            "<p>A background check goes deeper than an ID verification. It looks at the candidate's "
            "history — criminal record, previous employers, any reported incidents.</p>"
            "<h2>3. Call At Least Two Former Employers</h2>"
            "<p>References matter. A CV tells you what someone wants you to know. A phone call with "
            "a previous employer tells you what they actually experienced.</p>"
            "<h2>4. Conduct a Structured Interview</h2>"
            "<p>Many employers interview domestic staff the same way they'd chat with a neighbour — "
            "casually and without structure. Prepare a consistent set of questions.</p>"
            "<h2>5. Assess Their Relevant Skills</h2>"
            "<p>For a cook, ask them to prepare a simple meal during the interview. For a nanny, "
            "arrange a supervised interaction with your child.</p>"
            "<h2>6. Agree on Clear Terms Before They Start</h2>"
            "<p>Verbal agreements are the root cause of most domestic staff disputes in Nigeria. "
            "Write down and sign an agreement covering salary, hours, duties, and notice period.</p>"
            "<h2>7. Discuss Salary Honestly and Fairly</h2>"
            "<p>Underpaying domestic staff creates resentment and drives theft. Research the current "
            "going rate in your city for the role you are hiring.</p>"
            "<h2>8. Set Up a Probationary Period</h2>"
            "<p>Never go straight from interview to permanent hire. A 30 to 90-day probationary "
            "period protects both sides.</p>"
            "<h2>9. Install Basic Home Security</h2>"
            "<p>This is not about distrust — it is about creating a safe environment for everyone. "
            "Install at least one visible camera in common areas.</p>"
            "<h2>10. Treat Them With Dignity</h2>"
            "<p>The best domestic professionals choose their employers carefully and they leave bad "
            "ones quickly. Pay on time, provide adequate food and rest, and acknowledge good work.</p>"
        ),
        "tags": "Hiring Tips,Domestic Staff,NIN Verification,House Maid Nigeria,Background Check",
        "read_time": 7,
        "views": 2841,
        "is_featured": True,
        "is_published": True,
        "published_at": make_dt("2026-08-10"),
    },
    {
        "slug": "safely-introduce-new-live-in-maid-family",
        "title": "How to Safely Introduce a New Live-In Maid to Your Family",
        "excerpt": (
            "The first week with a new live-in maid sets the tone for the entire relationship. "
            "Here's how to make it smooth and safe for everyone."
        ),
        "category": "safety",
        "author_name": "Funke Adesanya",
        "author_avatar": "https://randomuser.me/api/portraits/women/65.jpg",
        "author_bio": "Funke covers domestic safety and household management topics for Nigerian families.",
        "cover_image": "https://images.unsplash.com/photo-1527515637462-cff94ebb95ac?w=800&q=80",
        "content": (
            "<p>Bringing a new live-in maid into your home requires careful planning and clear "
            "communication from day one. The tone you set in the first week often defines the "
            "entire working relationship.</p>"
            "<h2>Before They Arrive</h2>"
            "<p>Prepare a dedicated space for them — a clean room, storage for their belongings, "
            "and clarity about which areas of the home are private family spaces.</p>"
            "<h2>Day One Walkthrough</h2>"
            "<p>Walk them through the home together. Show them where supplies are kept, explain "
            "appliances, and introduce them to every family member calmly.</p>"
            "<h2>Set House Rules Early</h2>"
            "<p>Discuss phone usage, visiting hours, meal arrangements, and daily schedule on "
            "the first day. Write them down and give them a copy.</p>"
            "<h2>Give Them Time to Settle</h2>"
            "<p>Avoid overloading them with tasks in the first 48 hours. Let them observe the "
            "household rhythm before jumping into full duties.</p>"
        ),
        "tags": "Safety,Live-In Maid,New Hire,Introduction",
        "read_time": 5,
        "views": 1204,
        "is_featured": False,
        "is_published": True,
        "published_at": make_dt("2026-08-05"),
    },
    {
        "slug": "5-skills-domestic-professionals-stand-out-nigeria",
        "title": "5 Skills That Make Domestic Professionals Stand Out in Nigeria",
        "excerpt": (
            "From cooking skills to communication, these are the qualities employers "
            "look for most when hiring domestic staff in 2026."
        ),
        "category": "career",
        "author_name": "Taiwo Ogundimu",
        "author_avatar": "https://randomuser.me/api/portraits/men/32.jpg",
        "author_bio": "Taiwo writes career development content for domestic professionals across Nigeria.",
        "cover_image": "https://images.unsplash.com/photo-1507048331197-7d4ac70811cf?w=800&q=80",
        "content": (
            "<p>The domestic staffing market in Nigeria is competitive. Families have more "
            "choices than ever, and they are looking for professionals who bring more than "
            "basic competency to the role.</p>"
            "<h2>1. Strong Communication Skills</h2>"
            "<p>Being able to ask questions, report problems clearly, and follow instructions "
            "accurately is the number one quality employers mention.</p>"
            "<h2>2. Proactive Problem-Solving</h2>"
            "<p>Employers value staff who notice issues and address them without being told "
            "every time — a broken appliance reported early, a low supply restocked without prompting.</p>"
            "<h2>3. Child and Elderly Care Knowledge</h2>"
            "<p>Even for general house help roles, basic first aid awareness and sensitivity "
            "to vulnerable household members sets candidates apart.</p>"
            "<h2>4. Cooking Skills</h2>"
            "<p>The ability to prepare at least a handful of Nigerian staples confidently "
            "is highly valued even in non-cook roles.</p>"
            "<h2>5. Trustworthiness and Consistency</h2>"
            "<p>Showing up on time every day, being honest about mistakes, and maintaining "
            "confidentiality about the household are qualities that build long careers.</p>"
        ),
        "tags": "Career Advice,Domestic Professionals,Skills,Nigeria,Jobs",
        "read_time": 4,
        "views": 987,
        "is_featured": False,
        "is_published": True,
        "published_at": make_dt("2026-07-28"),
    },
    {
        "slug": "babysitter-vs-nanny-whats-right-for-your-family",
        "title": "Choosing Between a Babysitter and a Nanny: What's Right for Your Family?",
        "excerpt": (
            "Both provide childcare, but the differences matter. We break down costs, "
            "responsibilities, and what each option means for your household."
        ),
        "category": "family",
        "author_name": "Adaeze Okafor",
        "author_avatar": "https://randomuser.me/api/portraits/women/44.jpg",
        "author_bio": "Adaeze writes about domestic employment and household management across Nigeria.",
        "cover_image": "https://images.unsplash.com/photo-1555252333-9f8e92e65df9?w=800&q=80",
        "content": (
            "<p>Both babysitters and nannies provide childcare, but they are very different "
            "roles with different costs, expectations, and commitments.</p>"
            "<h2>What Is a Babysitter?</h2>"
            "<p>A babysitter typically provides short-term, occasional childcare — evenings, "
            "weekends, or specific hours when parents are unavailable. They are usually paid "
            "per session and do not live with the family.</p>"
            "<h2>What Is a Nanny?</h2>"
            "<p>A nanny is a full-time or part-time childcare professional who typically "
            "works regular hours within your home. They may or may not be live-in, and they "
            "usually take on a broader role including light housekeeping and school runs.</p>"
            "<h2>Cost Comparison</h2>"
            "<p>Babysitters in Lagos typically charge ₦3,000–₦8,000 per session. Nannies "
            "command ₦50,000–₦100,000 per month depending on experience and location.</p>"
            "<h2>Which Is Right for You?</h2>"
            "<p>If you need regular, structured childcare Monday to Friday, a nanny is the "
            "right choice. If you need occasional cover for evenings or weekends, a babysitter "
            "is more cost-effective and flexible.</p>"
        ),
        "tags": "Family Life,Babysitter,Nanny,Childcare,Nigeria",
        "read_time": 6,
        "views": 1543,
        "is_featured": False,
        "is_published": True,
        "published_at": make_dt("2026-07-20"),
    },
    {
        "slug": "domestic-staff-employment-contract-nigeria",
        "title": "What to Include in a Domestic Staff Employment Contract in Nigeria",
        "excerpt": (
            "A written contract protects both you and your employee. Here are the key "
            "clauses every domestic staff agreement should contain."
        ),
        "category": "hiring",
        "author_name": "Chukwuemeka Bello",
        "author_avatar": "https://randomuser.me/api/portraits/men/45.jpg",
        "author_bio": "Chukwuemeka is a labour relations writer focused on the Nigerian domestic employment sector.",
        "cover_image": "https://images.unsplash.com/photo-1576765608535-5f04d1e3f289?w=800&q=80",
        "content": (
            "<p>A written contract is the single most important document in any domestic "
            "employment relationship. Without one, disputes are nearly impossible to resolve "
            "fairly for either party.</p>"
            "<h2>Essential Clauses</h2>"
            "<p>Every domestic staff contract in Nigeria should include: full names and "
            "addresses of both parties, start date, job title and duties, working hours, "
            "salary and payment schedule, leave entitlements, and notice period.</p>"
            "<h2>Salary and Payment Terms</h2>"
            "<p>Specify the exact monthly salary, the date it will be paid each month, and "
            "the method of payment. Include any agreed allowances such as feeding or transport.</p>"
            "<h2>Working Hours and Rest Days</h2>"
            "<p>State the daily start and end times, weekly days off, and public holiday "
            "entitlements. For live-in staff, also define personal time and visitor policies.</p>"
            "<h2>Termination and Notice</h2>"
            "<p>Both parties should have a clear notice period — typically 1–4 weeks depending "
            "on length of service. Include grounds for immediate termination without notice.</p>"
            "<h2>Confidentiality</h2>"
            "<p>A simple confidentiality clause protecting family privacy is increasingly "
            "common and legally enforceable under Nigerian employment principles.</p>"
        ),
        "tags": "Hiring Tips,Contract,Employment,Legal,Nigeria",
        "read_time": 8,
        "views": 2107,
        "is_featured": False,
        "is_published": True,
        "published_at": make_dt("2026-07-12"),
    },
    {
        "slug": "video-interview-domestic-professional-guide",
        "title": "How to Conduct a Video Interview with a Domestic Professional",
        "excerpt": (
            "Video interviews save time and help you make better hiring decisions. "
            "Use this guide to get the most out of every virtual meeting."
        ),
        "category": "guides",
        "author_name": "Funke Adesanya",
        "author_avatar": "https://randomuser.me/api/portraits/women/65.jpg",
        "author_bio": "Funke covers domestic safety and household management topics for Nigerian families.",
        "cover_image": "https://images.unsplash.com/photo-1449965408869-eaa3f722e40d?w=800&q=80",
        "content": (
            "<p>Video interviews have become a standard part of the domestic hiring process "
            "in Nigeria. They save travel time, allow you to assess presentation and "
            "communication from a distance, and make it easy to interview multiple candidates "
            "in a single day.</p>"
            "<h2>Choose the Right Platform</h2>"
            "<p>WhatsApp Video, Zoom, and Google Meet all work well. Choose whichever the "
            "candidate is comfortable with — forcing someone to use an unfamiliar app "
            "disadvantages them unfairly.</p>"
            "<h2>Prepare Your Questions in Advance</h2>"
            "<p>Write down 8–10 specific questions covering experience, availability, "
            "salary expectations, and situational scenarios. Take notes during the call.</p>"
            "<h2>Assess Beyond the Answers</h2>"
            "<p>Pay attention to punctuality, how they present themselves, clarity of speech, "
            "and how they respond to follow-up questions. These tell you as much as the answers.</p>"
            "<h2>End With Next Steps</h2>"
            "<p>Always tell the candidate what happens next — a second interview, a practical "
            "test, or a decision timeline. Leaving them uncertain is disrespectful and "
            "damages your reputation as an employer.</p>"
        ),
        "tags": "How-To Guides,Video Interview,Hiring,Domestic Staff",
        "read_time": 4,
        "views": 876,
        "is_featured": False,
        "is_published": True,
        "published_at": make_dt("2026-07-05"),
    },
    {
        "slug": "building-professional-domestic-career-nigeria",
        "title": "Building a Professional Domestic Career: A Guide for Nigerian Helpers",
        "excerpt": (
            "Domestic work is a skilled profession. Discover how to build your reputation, "
            "get better opportunities, and grow your career with SelectRoyal Maids."
        ),
        "category": "career",
        "author_name": "Taiwo Ogundimu",
        "author_avatar": "https://randomuser.me/api/portraits/men/32.jpg",
        "author_bio": "Taiwo writes career development content for domestic professionals across Nigeria.",
        "cover_image": "https://images.unsplash.com/photo-1587691592099-24045742c181?w=800&q=80",
        "content": (
            "<p>Domestic work is one of Nigeria's most important employment sectors, yet it "
            "remains one of the least professionalised. That is changing — and those who "
            "treat it as a career rather than a stop-gap are reaping the rewards.</p>"
            "<h2>Build a Professional Profile</h2>"
            "<p>Create a complete profile on SelectRoyal Maids with a professional photo, "
            "detailed work history, and specific skills listed. Employers make decisions "
            "within seconds of viewing a profile.</p>"
            "<h2>Collect References Proactively</h2>"
            "<p>After each placement, ask your employer for a written reference. Build a "
            "folder of these over time — it becomes your most powerful career asset.</p>"
            "<h2>Learn New Skills Continuously</h2>"
            "<p>Basic first aid, cooking courses, child development knowledge, and even "
            "driving lessons can all dramatically increase your earning potential.</p>"
            "<h2>Be Reliable Above All Else</h2>"
            "<p>In domestic work, reliability is the single most valued quality. Show up "
            "on time every day, communicate proactively when problems arise, and do what "
            "you say you will do.</p>"
            "<h2>Know Your Rights</h2>"
            "<p>You are entitled to fair pay, rest days, and a safe working environment. "
            "If an employer is not meeting these basics, SelectRoyal Maids can help you "
            "find a better placement.</p>"
        ),
        "tags": "Career Advice,Domestic Professionals,Nigeria,Skills,Growth",
        "read_time": 5,
        "views": 1389,
        "is_featured": False,
        "is_published": True,
        "published_at": make_dt("2026-06-28"),
    },
]


def seed_posts(apps, schema_editor):
    BlogPost = apps.get_model("MaidApp", "BlogPost")
    for data in POSTS:
        BlogPost.objects.get_or_create(slug=data["slug"], defaults=data)


def unseed_posts(apps, schema_editor):
    BlogPost = apps.get_model("MaidApp", "BlogPost")
    for data in POSTS:
        BlogPost.objects.filter(slug=data["slug"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("MaidApp", "0007_blogpost_model"),
    ]

    operations = [
        migrations.RunPython(seed_posts, reverse_code=unseed_posts),
    ]
