"""Everyday conversational words the course must teach early.

The list CONVERSATION_PLAN.md measured the old deck against (step 1): 214
common words for greeting, politeness, introductions, eating out, shopping,
travel, time, family, health and feelings, plus the connecting words of
ordinary talk. On the old deck 110 of them were missing, optional, or more
than a month away. tools/measure_conversation.py reports where each is
taught now, and tools/test_conversation_core.py fails if one drops out of
the Conversation Core.

An entry counts as taught when the core teaches the word itself, a word it
is a form of (`pëlqen` is `pëlqej`), or a phrase that contains it (`s'ka`).
"""

WORDS = """
faleminderit ju lutem përshëndetje mirëmëngjes mirëdita mirëmbrëma natën
mirupafshim tungjatjeta ç'kemi mirë keq po jo ndoshta sigurisht patjetër
dakord në rregull ok se vini mirësevini gëzuar urime më fal falni ndjesë
vjen s'ka gjë asgjë të quhem emër flisni shqip anglisht kuptoj di dua duhet
mund pëlqen pëlqej dashuroj dashuri nevojë ndihmë ndihmoj sa kushton lek
para çmim shtrenjtë lirë hap mbyll majtas djathtas drejt afër larg tualet
banjë restorant hotel rrugë stacion autobus tren aeroport biletë ujë kafe
çaj bukë faturë llogari uri etje lodhur sëmurë mjek spital farmaci telefon
numër ftohtë nxehtë ngrohtë shi diell mot shok shoqe mik familje burrë grua
fëmijë prind gjysh gjyshe ushqim darkë drekë mëngjes shije shijshëm tash
tani pastaj vonë herët gjithmonë kurrë shpesh sërish prapë shpejt ngadalë
pak shumë mjaft tepër bashkë vetëm sepse prandaj megjithatë gjithsesi jetoj
punoj mësoj lexoj shkruaj blej shes paguaj pres kërkoj gjej harroj kujtoj
takoj njoh thërras pyes përgjigjem fle zgjohem luaj eci vrapoj udhëtoj
qëndroj kthehem hyj dal ulem ngrihem mbaroj filloj provoj ndiej besoj
shpresoj mendoj lumtur trishtuar lehtë vështirë rëndësishëm mundur gabim
saktë drejtë shqiptar Shqipëri Kosovë gjuhë fjalë kuptim pyetje përgjigje
mos ky kjo ai ajo këtu atje aty tjetër çdo asnjë dikush diçka askush
gjithçka javë fundjavë muaj pasdite mbrëmje natë ora sekondë minutë
""".split()

# Deliberately not taught, each for a stated reason.
SKIPPED = {
    "tungjatjeta": "dated; përshëndetje and mirëdita are what people say",
    "ok": "English, understood everywhere, nothing to learn",
    "dashuroj": "the core teaches dua, the everyday verb for 'to love'",
    "shije": "the core teaches shijshëm (tasty), the form used at the table",
    "tash": "a regional variant of tani, which the core teaches",
}
