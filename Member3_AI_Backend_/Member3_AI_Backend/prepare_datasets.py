"""Create fixed, auditable train/validation/test datasets.

The legacy expanded CSV is intentionally not read or overwritten.  Each split
uses independently authored scenario sentences.  Only neutral style variants
are generated, and variants from one semantic group stay in one split.
"""

from __future__ import annotations

import csv
from difflib import SequenceMatcher
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
FIELDS = ["complaint", "category", "priority", "group_id"]
CATEGORIES = {
    "technical_support",
    "account_access",
    "billing_payment",
    "delivery_order",
    "general_enquiry",
}
PRIORITIES = {"high", "medium", "low"}


TRAIN_BASES: dict[tuple[str, str], list[str]] = {
    ("account_access", "high"): [
        "Someone changed my password and recovery email, and now I am locked out.",
        "I can see logins from another country and my account settings were altered.",
        "My account has been hacked and the intruder enabled their own two-factor device.",
        "An unknown person took over my profile and removed my sign-in options.",
        "I did not reset my password, but it was changed and I cannot get back in.",
        "My recovery phone now belongs to someone else and the account is compromised.",
        "A person I do not know changed the login credentials and locked me out.",
        "The account is sending messages by itself after an unfamiliar security change.",
    ],
    ("account_access", "medium"): [
        "The password reset email has not arrived after several attempts.",
        "My correct verification code keeps being rejected on my own account.",
        "I am temporarily locked out after entering the wrong password too many times.",
        "The sign-in page loops back to login even though my password is correct.",
        "I replaced my phone and need help restoring my authenticator access.",
        "My profile email will not update and I need it corrected this week.",
        "I can log in on the website but the mobile sign-in rejects the same credentials.",
        "The account recovery form cannot verify my legitimate identity document.",
    ],
    ("account_access", "low"): [
        "How do I enable two-factor authentication on my profile?",
        "Where can I view my recent account login history?",
        "I would like instructions for changing my display name.",
        "Can I remove an old phone number from my account settings?",
        "What are the password length and character requirements?",
        "How can I close an unused account that I can still access?",
        "Can I choose a different username without opening a new account?",
        "Where is the setting for routine sign-in notifications?",
    ],
    ("billing_payment", "high"): [
        "A transfer of USD 90000 left my bank account without my permission.",
        "My stolen card is being used for several payments that are not mine.",
        "RM75,000 was deducted from my account and I never approved the transaction.",
        "Someone made a fraudulent payment using my saved card details.",
        "The service withdrew $100000 from my bank even though I authorised no purchase.",
        "My card was charged repeatedly and the total has emptied my account.",
        "A bank transfer I never made removed RM 1 million from my balance.",
        "There is a huge cash withdrawal on the statement that I did not authorise.",
    ],
    ("billing_payment", "medium"): [
        "My refund was approved last week but it still has not reached my card.",
        "Payment fails each time I try to finish the order.",
        "I was charged twice for a small purchase and need one charge reversed.",
        "The invoice total does not match the price shown at checkout.",
        "A cancelled monthly subscription was billed again this month.",
        "My promocode worked on screen but the discount is missing from the receipt.",
        "The refund money has not arrived in my account even though the return was accepted.",
        "I am still waiting for a refund that the merchant marked as processed.",
    ],
    ("billing_payment", "low"): [
        "What payment methods do you accept?",
        "Can I pay an invoice using a debit card?",
        "Where can I download another copy of my receipt?",
        "How do I replace the saved card used for future payments?",
        "Which currencies can be used at checkout?",
        "When does the normal monthly billing cycle begin?",
        "Is there a minimum amount for paying by bank transfer?",
        "Can you explain where to find the billing date on an invoice?",
    ],
    ("delivery_order", "high"): [
        "My temperature-sensitive medicine never arrived and the replacement is needed today.",
        "The parcel contains broken glass and leaking chemicals, so it may be unsafe.",
        "A valuable package was marked delivered to a stranger and is now missing.",
        "The courier left my passport shipment at the wrong building.",
        "An essential medical device is lost after the tracking stopped for a week.",
        "The food delivery arrived with damaged packaging and signs of contamination.",
        "A live-saving prescription parcel is missing and the patient has no spare supply.",
        "The courier delivered a badly crushed gas canister that could be dangerous.",
    ],
    ("delivery_order", "medium"): [
        "My regular parcel is four days late and tracking has not changed.",
        "The order arrived with one item missing from the box.",
        "I received the wrong size and need an exchange.",
        "Tracking says delivered, but the package is not at my door.",
        "The courier attempted delivery while I was home and did not call.",
        "My order has stayed at the sorting centre since Monday.",
        "The parcel came two days late and one accessory was not included.",
        "I need help finding an ordinary shipment whose tracking is stuck.",
    ],
    ("delivery_order", "low"): [
        "How much is standard delivery to Kuala Lumpur?",
        "Can two orders be combined before they are shipped?",
        "What is the usual delivery time for local orders?",
        "Where do I enter a different shipping address?",
        "Do you offer collection from a nearby service point?",
        "Which courier company handles normal parcels?",
        "Is signature confirmation available as a delivery option?",
        "Can the delivery date be selected before I place an order?",
    ],
    ("technical_support", "high"): [
        "The entire platform is offline for every employee in our company.",
        "All users see a blank page and none of our staff can access the service.",
        "A system update erased our shared production data and there is no backup visible.",
        "The service has a complete outage across every office location.",
        "Everyone in our organisation is locked out because the authentication server is down.",
        "Our public application is unavailable to all customers after the latest release.",
        "The whole network service is down, leaving every department unable to work.",
        "A failed deployment destroyed the complete shared dataset used by all users.",
    ],
    ("technical_support", "medium"): [
        "The mobile app crashes whenever I open the reports screen.",
        "File upload reaches ninety percent and then fails on my laptop.",
        "The website is very slow for me during the afternoon.",
        "Notifications stopped appearing even though they are enabled.",
        "Video playback freezes every few minutes on one device.",
        "The export button does nothing in my browser.",
        "One dashboard widget shows an error while the rest of the system works.",
        "The app closes on my phone when I try to save a new record.",
    ],
    ("technical_support", "low"): [
        "Where can I find the desktop application user guide?",
        "Does the software support an older version of Windows?",
        "How do I change the interface language?",
        "Can dark mode be enabled on the mobile app?",
        "What file formats are supported for uploads?",
        "Is there a keyboard shortcut for opening search?",
        "Where can I read the API format documentation?",
        "Does the desktop program have an automatic update setting?",
    ],
    ("general_enquiry", "high"): [
        "I need product safety information because the device is overheating near a child.",
        "A recall notice mentions this model, but the safety instructions are unavailable.",
        "We need confirmation today for a legal filing that closes in a few hours.",
        "A customer with a medical accessibility need cannot find the emergency support channel.",
        "The published allergy information conflicts with the product label.",
        "I need immediate clarification about a safety warning before the equipment is used.",
        "The product guide gives no first-aid advice after contact with the leaking material.",
        "A regulatory submission closes today and the required compliance answer is missing.",
    ],
    ("general_enquiry", "medium"): [
        "I need help choosing a service package for a small business.",
        "Could someone clarify the documents needed for my application?",
        "I am waiting for confirmation of an appointment scheduled this week.",
        "A business enquiry sent several days ago has not received a reply.",
        "Please explain which support plan includes weekend assistance.",
        "I need advice comparing the standard and premium services.",
        "Could an adviser explain the eligibility conditions for this programme?",
        "My scheduled consultation needs a confirmed time before the end of the week.",
    ],
    ("general_enquiry", "low"): [
        "What time does the customer service centre open?",
        "Where is the nearest branch located?",
        "How can I contact the sales team?",
        "Are your offices open on public holidays?",
        "What services are included in the basic package?",
        "Is there a general telephone number for enquiries?",
        "Where can I see the normal price list for your service packages?",
        "Do you publish a calendar of office closure dates?",
    ],
}


VALIDATION_BASES: dict[tuple[str, str], list[str]] = {
    ("account_access", "high"): [
        "A stranger replaced both my login password and backup address.",
        "My profile was taken over overnight and I no longer control its security settings.",
        "There are unknown sessions in my account and the recovery details are not mine.",
    ],
    ("account_access", "medium"): [
        "My authenticator codes suddenly fail, but I still control the email address.",
        "I cannot sign in after changing phones and need recovery assistance.",
        "The reset link says expired as soon as I open it.",
    ],
    ("account_access", "low"): [
        "Please show me how to update my profile photograph.",
        "Can users rename their account after registration?",
        "Where is the option to review active devices?",
    ],
    ("billing_payment", "high"): [
        "I found a fraudulent USD 65000 card purchase that I did not approve.",
        "Someone transferred RM100000 from my balance without consent.",
        "Unknown charges have consumed nearly all of the money in my bank account.",
    ],
    ("billing_payment", "medium"): [
        "The refund status says completed, although no money has arrived.",
        "Checkout declined two valid cards and I cannot place the order.",
        "My annual plan renewed after I requested cancellation.",
    ],
    ("billing_payment", "low"): [
        "Do you support bank transfers for ordinary invoices?",
        "How can I print a tax receipt?",
        "May I change the currency displayed on the payment page?",
    ],
    ("delivery_order", "high"): [
        "A box of prescription supplies went to the wrong address and cannot be found.",
        "The delivered battery is swollen and the parcel is hot to touch.",
        "My confidential identity documents were left outside another home.",
    ],
    ("delivery_order", "medium"): [
        "The tracking page has shown customs processing for six days.",
        "One product in my shipment is different from what I ordered.",
        "My package missed its expected arrival date this week.",
    ],
    ("delivery_order", "low"): [
        "Do weekend deliveries cost extra?",
        "Can I select a parcel locker during checkout?",
        "How long is economy shipping normally?",
    ],
    ("technical_support", "high"): [
        "Our whole organisation has been offline since the database failure.",
        "Every customer receives a service unavailable page across the platform.",
        "The latest upgrade deleted all shared project records for our team.",
    ],
    ("technical_support", "medium"): [
        "Search returns an error only when I filter by date.",
        "The desktop client disconnects a few times each hour.",
        "I cannot attach a PDF even though smaller files work.",
    ],
    ("technical_support", "low"): [
        "Is the application available for Linux?",
        "Where are notification preferences located?",
        "Can I increase the text size in settings?",
    ],
    ("general_enquiry", "high"): [
        "The manual omits what to do after smoke comes from the product.",
        "We need a safety certificate before equipment inspection this afternoon.",
        "Please confirm whether this batch is included in the health recall.",
    ],
    ("general_enquiry", "medium"): [
        "Which plan would suit a team of twenty people?",
        "My application needs one document clarified before Friday.",
        "I have not received the date for my upcoming consultation.",
    ],
    ("general_enquiry", "low"): [
        "Is live chat available during the weekend?",
        "What is the mailing address of your main office?",
        "Where can I read an overview of your services?",
    ],
}


TEST_BASES: dict[tuple[str, str], list[str]] = {
    ("account_access", "high"): [
        "I think my acct got hijacked; somebody swapped the recovery email.",
        "An intruder changed my password while I was asleep and now owns the login.",
        "The security page shows a device I do not recognise, and my backup number was replaced.",
        "cant get in anymore because another person reset all my sign-in details",
        "My account is compromised and messages are being sent under my name.",
    ],
    ("account_access", "medium"): [
        "2fa codes are not working after I moved to a new handset.",
        "The login link keeps expiring before the page loads.",
        "I still own the account, but it has been locked since yesterday.",
        "Why does the sign-in form keep returning me to the same screen?",
        "Recovery mail is delayed and I need access for work tomorrow.",
    ],
    ("account_access", "low"): [
        "Where do I turn on login alerts?",
        "I'd like to edit the name shown on my profile.",
        "How many devices may stay signed in at once?",
        "Can I add a second recovery phone number?",
        "Please point me to the account deletion instructions.",
    ],
    ("billing_payment", "high"): [
        "A card payment for $87,500 appeared while the card was locked in my drawer.",
        "Fraudsters withdrew RM60000 from my bank balance.",
        "Three payments I never authorised have taken my entire salary.",
        "usd 120000 was transferred out and I have no idea who did it",
        "My bank shows a massive card debit that definitely isn't mine.",
    ],
    ("billing_payment", "medium"): [
        "It's been nine days and the approved refund is still missing.",
        "My checkout payment keeps failing with a valid card.",
        "Could you correct a duplicate $25 charge on yesterday's order?",
        "The subscription cancellation did not stop this month's bill.",
        "My reciept shows the wrong discount and total.",
    ],
    ("billing_payment", "low"): [
        "Is PayPal one of the available ways to pay?",
        "Where is the button for downloading old invoices?",
        "Can prices be displayed in Malaysian ringgit?",
        "When will the next routine subscription invoice be issued?",
        "Do debit cards have an extra processing fee?",
    ],
    ("delivery_order", "high"): [
        "The courier lost the insulin shipment that must stay refrigerated.",
        "My parcel is leaking an unknown liquid and smells like chemicals.",
        "A package containing my immigration documents went to someone else.",
        "The replacement part for essential medical equipment is missing in transit.",
        "Broken glass is sticking through the box that was just delivered.",
    ],
    ("delivery_order", "medium"): [
        "Trackng hasn't moved for nearly a week; where is my parcel?",
        "Only two of the three products were inside the delivery box.",
        "The driver marked it delivered, but nothing is outside my flat.",
        "I ordered blue and received the same product in red.",
        "The estimated date passed three days ago for a normal order.",
    ],
    ("delivery_order", "low"): [
        "What would regular postage cost to Penang?",
        "Is store pickup available instead of home delivery?",
        "May I alter the address before dispatch?",
        "Which company transports your standard shipments?",
        "Roughly how many days does local shipping take?",
    ],
    ("technical_support", "high"): [
        "Our platform is completely down and every user gets an offline message.",
        "Nobody across the company can open the service at all.",
        "All customer-facing systems stopped working at the same time.",
        "The production update wiped the shared records for the entire team.",
        "Every branch has lost access because the central server is unavailable.",
    ],
    ("technical_support", "medium"): [
        "app crashes when i tap the analytics tab",
        "Uploads stall at the end, but everything else works.",
        "The site becomes sluggish on my computer after lunch.",
        "I no longer receive alerts for new messages.",
        "Exporting a spreadsheet gives me an error in Chrome.",
    ],
    ("technical_support", "low"): [
        "Does this tool run on macOS?",
        "How can I switch the app to Bahasa Melayu?",
        "Where's the documentation for keyboard commands?",
        "Is high-contrast mode supported?",
        "Which image types can be uploaded?",
    ],
    ("general_enquiry", "high"): [
        "The charger is sparking; where are the product safety directions?",
        "Is this serial number part of the dangerous-device recall?",
        "We need the compliance statement before today's legal deadline.",
        "A severe allergy warning differs between your website and packaging.",
        "Where can a disabled customer get immediate safety assistance?",
    ],
    ("general_enquiry", "medium"): [
        "Could an adviser help pick a plan for our new office?",
        "One requirement in the application form is unclear.",
        "I am still waiting to learn when this week's appointment will be.",
        "Can someone compare the benefits of two service packages?",
        "Our partnership question has gone unanswered for several days.",
    ],
    ("general_enquiry", "low"): [
        "What are the weekday opening hours?",
        "How do I reach your general enquiries team?",
        "Is there a branch anywhere near Ipoh?",
        "Where can I see a list of the services you provide?",
        "Are support centres closed on national holidays?",
    ],
}


TRAIN_STYLES = [
    lambda text: text,
    lambda text: f"Hi support, {text[0].lower()}{text[1:]}",
    lambda text: f"hey, {text[0].lower()}{text[1:]} can someone check?",
    lambda text: (
        f"{text} I checked the help page and tried the usual steps, but I still "
        "need a clear answer from support."
    ),
    lambda text: f"Can you look into this for me: {text[0].lower()}{text[1:]}",
]

VALIDATION_STYLES = [
    lambda text: text,
    lambda text: f"Hello team — {text[0].lower()}{text[1:]} Please advise.",
]


def build_rows(
    split: str,
    bases: dict[tuple[str, str], list[str]],
    styles,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for (category, priority), messages in sorted(bases.items()):
        for message_index, message in enumerate(messages, start=1):
            group_id = f"{split}-{category}-{priority}-{message_index:02d}"
            for style_index, style in enumerate(styles, start=1):
                rows.append(
                    {
                        "complaint": style(message),
                        "category": category,
                        "priority": priority,
                        "group_id": group_id,
                    }
                )
    return rows


def normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def assert_valid_splits(splits: dict[str, list[dict[str, str]]]) -> None:
    all_rows = [row for rows in splits.values() for row in rows]
    complaints = [normalize(row["complaint"]) for row in all_rows]
    if len(complaints) != len(set(complaints)):
        raise RuntimeError("An exact normalized complaint appears more than once.")

    for row in all_rows:
        if row["category"] not in CATEGORIES or row["priority"] not in PRIORITIES:
            raise RuntimeError(f"Unexpected label in row: {row}")

    split_names = list(splits)
    for left_index, left_name in enumerate(split_names):
        left_groups = {row["group_id"] for row in splits[left_name]}
        for right_name in split_names[left_index + 1 :]:
            right_groups = {row["group_id"] for row in splits[right_name]}
            if left_groups & right_groups:
                raise RuntimeError(f"Group leakage between {left_name} and {right_name}.")

            for left in splits[left_name]:
                left_text = normalize(left["complaint"])
                for right in splits[right_name]:
                    right_text = normalize(right["complaint"])
                    similarity = SequenceMatcher(None, left_text, right_text).ratio()
                    if similarity >= 0.90:
                        raise RuntimeError(
                            "Near-identical cross-split complaints detected: "
                            f"{left_name}={left['complaint']!r}; "
                            f"{right_name}={right['complaint']!r}; "
                            f"similarity={similarity:.3f}"
                        )


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    splits = {
        "train": build_rows("train", TRAIN_BASES, TRAIN_STYLES),
        "validation": build_rows(
            "validation", VALIDATION_BASES, VALIDATION_STYLES
        ),
        "test": build_rows("test", TEST_BASES, [lambda text: text]),
    }
    assert_valid_splits(splits)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for split_name, rows in splits.items():
        path = DATA_DIR / f"customer_support_tickets_{split_name}.csv"
        write_rows(path, rows)
        print(f"{split_name}: {len(rows)} rows -> {path}")


if __name__ == "__main__":
    main()
