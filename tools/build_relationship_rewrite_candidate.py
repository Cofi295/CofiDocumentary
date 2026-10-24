from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(r"B:\ALL_TOOLS\CofiDocumentary")
JOB_ID = "20260911-151108-5894066c"
OUT = ROOT / "workspaces" / JOB_ID / ".relationship_rewrite_candidate3"


SOURCES = {
    "mercer": "https://erpapers.columbian.gwu.edu/lucy-page-mercer-rutherfurd-1891-1948",
    "fdr": "https://erpapers.columbian.gwu.edu/franklin-delano-roosevelt-1882-1945",
    "eleanor": "https://erpapers.columbian.gwu.edu/short-biography-eleanor-roosevelt",
    "valkill": "https://www.nps.gov/articles/000/val-kill-650024.htm",
    "anderson": "https://www.fdrlibrary.org/anderson",
    "miller": "https://millercenter.org/president/fdroosevelt/family-life",
    "udhr": "https://www.un.org/en/about-us/udhr/drafters-of-the-declaration",
}


SECTIONS = [
    {
        "group": "warm-springs-secret-revealed",
        "purpose": "Cold open on the final secret and make the marriage mystery explicit.",
        "priority": "must_real",
        "queries": [
            "Franklin Roosevelt Warm Springs April 12 1945 final portrait",
            "Lucy Mercer Rutherfurd Warm Springs 1945 Franklin Roosevelt",
            "Eleanor Roosevelt Franklin Roosevelt funeral train 1945",
        ],
        "refs": [SOURCES["mercer"], SOURCES["fdr"]],
        "visual": "Authentic 1945 Warm Springs photographs, Franklin Roosevelt's unfinished portrait, Lucy Mercer Rutherfurd archival portrait, Eleanor Roosevelt, funeral-train and Little White House context.",
        "text": """
On April 12, 1945, Franklin Delano Roosevelt sat for a portrait at the Little White House in Warm Springs, Georgia. He was exhausted, visibly thinner than the man Americans knew from campaign photographs, and only weeks away from victory in Europe. Artist Elizabeth Shoumatoff was working when Roosevelt suddenly complained of a terrible pain in the back of his head. Within hours, the president was dead.

The official story was national tragedy: a wartime president collapsing just before the end of the war. Inside the Roosevelt family, there was another story. One of the people who had been with Franklin at Warm Springs was Lucy Mercer Rutherfurd. She was not a new friend. She was the woman whose relationship with Franklin had nearly ended his marriage twenty-seven years earlier.

Eleanor Roosevelt was in Washington when the call came. She traveled south believing she was going to meet the consequences of her husband's death. Instead, she also learned that an old promise had quietly been broken. Lucy had returned to Franklin's life, meetings had been arranged without Eleanor's knowledge, and their daughter Anna had helped make some of those meetings possible.

That detail changes the familiar Roosevelt photographs. Franklin and Eleanor appear in them as one of the most consequential political couples in American history. But by 1945, their marriage was not a conventional romance held together by recovered trust. It was a forty-year arrangement built from affection, betrayal, family obligation, separate friendships, political usefulness, secrecy, and a public partnership neither of them could easily replace.

So the real question is not simply why Franklin cheated, or why Eleanor was hurt. The harder question is why she stayed after discovering the affair in 1918—and what kind of marriage could survive long enough for the same woman to be present, in secret, when Franklin died.
""",
    },
    {
        "group": "marriage-before-lucy",
        "purpose": "Establish the family system and why divorce carried unusual cost.",
        "priority": "must_real",
        "queries": [
            "Franklin Eleanor Roosevelt wedding 1905 Theodore Roosevelt",
            "Sara Delano Roosevelt Franklin Eleanor New York townhouse",
            "Franklin Eleanor Roosevelt young family archival photographs",
        ],
        "refs": [SOURCES["eleanor"], SOURCES["miller"]],
        "visual": "Authentic early Roosevelt family photographs: wedding, young Franklin and Eleanor, Sara Delano Roosevelt, Hyde Park and the adjoining New York homes.",
        "text": """
To understand why leaving was so complicated, go back to the marriage Eleanor thought she had entered. Franklin and Eleanor were distant cousins from two branches of the Roosevelt family. She was Theodore Roosevelt's niece, a young woman shaped by the early deaths of both parents and by an education that had given her a wider view of the world than New York society usually encouraged in women of her class.

Franklin was charming, ambitious, and protected by wealth. His mother, Sara Delano Roosevelt, was also one of the strongest forces in his life. Franklin and Eleanor married on March 17, 1905. Theodore Roosevelt gave the bride away, and the famous family name made the wedding public before Franklin himself had done anything to deserve national attention.

Marriage brought privilege, but not much privacy. Sara remained closely involved in the young household. The couple's New York home adjoined hers, and family money made independence from her more theoretical than absolute. Between 1906 and 1916, Franklin and Eleanor had six children, one of whom died in infancy. Eleanor's identity was increasingly tied to motherhood, household duty, and the political career Franklin was beginning to build.

By 1913, Franklin was assistant secretary of the Navy in the Wilson administration. Washington gave him status, travel, and a social world beyond home. It also brought Lucy Mercer into Eleanor's orbit. Lucy was a young woman hired as Eleanor's social secretary. She was not an anonymous stranger encountered far from the family. She worked close enough to know the household from the inside.

Hold on to that fact. When the crisis came, Eleanor would not discover only that Franklin had another woman. She would discover that the boundary between her marriage and the affair had already been crossed inside her own home.
""",
    },
    {
        "group": "affair-discovery-1918",
        "purpose": "Make the discovery itself the central turning point rather than rushing into politics.",
        "priority": "must_real",
        "queries": [
            "Lucy Mercer archival portrait 1918",
            "Franklin Roosevelt World War I Washington 1918 Navy",
            "Eleanor Roosevelt 1918 archival photograph",
        ],
        "refs": [SOURCES["mercer"], SOURCES["fdr"], SOURCES["eleanor"]],
        "visual": "Archival portraits of Lucy Mercer, Eleanor and Franklin around World War I, Navy Department and wartime Washington context, luggage/letters only as clearly labeled illustrative detail when no authentic image exists.",
        "text": """
In 1918, Franklin returned from a trip ill with pneumonia. Eleanor unpacked his luggage. Inside were letters from Lucy Mercer. Institutional biographies of the Roosevelts describe the discovery as the moment Eleanor learned that the relationship between Franklin and Lucy had gone far beyond ordinary friendship.

The letters made denial difficult. Eleanor knew Lucy. Lucy had worked for her. The betrayal therefore carried two injuries at once: a husband's deception and the collapse of trust inside Eleanor's own circle. She confronted Franklin and offered him a divorce.

There was another humiliation built into the discovery. Eleanor had spent years adapting herself to a household in which Franklin's ambitions and Sara Roosevelt's authority often set the terms. Lucy had entered that household through Eleanor, not through some distant political club. The affair made Eleanor confront how little control she had possessed over a life that looked privileged from the outside.

This is where many retellings race ahead to the future and say the marriage survived. That word is too clean. A marriage can continue on paper while the assumptions that created it disappear. In 1918, divorce was not simply a private decision between two adults. For a rising politician from a wealthy, famous family, it threatened reputation, finances, custody arrangements, social standing, and a career Franklin clearly wanted to continue.

Sara Roosevelt strongly opposed a divorce. Political allies had every reason to fear scandal. Franklin had children, a family name, and ambitions that depended on respectability. Eleanor had children too, fewer independent financial choices than a modern retelling can easily imagine, and a public culture that would examine her decision as fiercely as his behavior.

No surviving document can reduce Eleanor's motives to one sentence. She was hurt, but hurt does not automatically reveal what she wanted most. She had children to protect, a complicated bond with Franklin, her own growing interest in public work, and a family structure in which every option carried a cost. What the record does show is the decision: Franklin and Eleanor did not divorce.

Nor does staying prove instant forgiveness. The distinction is important because public couples are often judged as though only two outcomes exist: leave and reject the betrayal, or stay and accept it. Eleanor chose neither so neatly. She remained in the legal marriage while changing the amount of authority that marriage would have over the rest of her life.

The terms mattered. Biographical accounts describe Franklin as promising to end the relationship with Lucy. The couple remained married, but the old model of the marriage did not simply restart. Trust had been damaged in a way neither later photographs nor political success could erase.

That is the first major reversal in Eleanor's story. Staying did not mean returning to the role she had occupied before the letters. The marriage continued, but the space inside it widened. Over time, Eleanor built friendships, political relationships, work, travel, and eventually a home life that belonged much more clearly to her.

The affair did not magically create an independent Eleanor Roosevelt. She already had intelligence, reform interests, and experience outside elite drawing rooms. But the discovery made one thing unmistakable: the marriage could no longer be the only structure around which her adult identity was organized.
""",
    },
    {
        "group": "why-eleanor-stayed",
        "purpose": "Answer the title-level mystery with documented pressures and the change in the marriage.",
        "priority": "prefer_real",
        "queries": [
            "Eleanor Franklin Roosevelt family Hyde Park 1920 archival",
            "Eleanor Roosevelt political women 1920s archival",
            "Franklin Roosevelt family photographs 1920",
        ],
        "refs": [SOURCES["eleanor"], SOURCES["miller"]],
        "visual": "Roosevelt family, Hyde Park, Eleanor's 1920s political networks and women organizers; use correct people and period rather than literal reenactment of private motives.",
        "text": """
Why, then, did Eleanor stay? Part of the answer is structural. Divorce would have detonated Franklin's political future at a moment when public scandal carried different consequences than it does now. Part was family: six children had been born into the marriage, and five survived infancy. Part was money and the Roosevelt family system. Part was social expectation. And part was the fact that Eleanor's feelings toward Franklin cannot be measured only by the injury he caused her.

Staying also gave Eleanor something historians sometimes miss when they ask the question only in romantic terms: time to build power of her own. She did not have to win a public divorce in order to stop living as an extension of Franklin. She could remain inside the family and gradually change what her life contained.

That choice also preserved access to a world Eleanor was beginning to understand politically. Franklin's career connected her to party leaders, reformers, reporters and public institutions. Remaining married kept that network close. But access alone would not have made her powerful. The crucial change was that she increasingly used the access to build relationships and credibility that belonged to her, not merely to Mrs. Franklin D. Roosevelt.

In the years after 1918, she expanded her work with political organizations and reformers. She learned the mechanics of speeches, campaigns, newspapers, meetings, patronage, and coalition building. These were not decorative First Lady skills. They were the tools of someone becoming a political actor.

The emotional geography changed too. Eleanor developed close friendships and independent circles that Franklin did not control. The couple could share children, public obligations, political conversation, and moments of genuine loyalty while no longer expecting the marriage to supply every form of companionship.

Their children grew up inside that ambiguity. The Roosevelts remained a family, yet the adults around them increasingly maintained separate confidants and separate routines. That matters later, when Anna helps Franklin see Lucy again. The secrecy of 1945 did not appear suddenly; it became possible inside a family that had spent decades learning how to live with compartments.

That arrangement can look cold if judged against a single ideal of marriage. It was also practical. The Roosevelts did not need the same private life in order to remain useful to each other. In fact, the distance between them would eventually become one of the sources of Eleanor's unusual influence.

But before the White House, another crisis made that arrangement even more consequential. In 1921, Franklin lost the unaided use of his legs after a paralytic illness historically diagnosed as polio. Suddenly, the man who had betrayed Eleanor also needed a political world that could operate beyond the limits of his body.
""",
    },
    {
        "group": "polio-and-two-centers",
        "purpose": "Show how the broken marriage became a functional two-center political partnership.",
        "priority": "must_real",
        "queries": [
            "Franklin Roosevelt polio 1921 Warm Springs archival",
            "Eleanor Roosevelt campaigning 1920s archival",
            "Eleanor Roosevelt Val-Kill Nancy Cook Marion Dickerman archival",
        ],
        "refs": [SOURCES["fdr"], SOURCES["eleanor"], SOURCES["valkill"]],
        "visual": "Authentic Franklin Roosevelt rehabilitation/Warm Springs imagery, Eleanor campaigning and speaking in the 1920s, Val-Kill and her independent circle.",
        "text": """
Franklin's illness could have ended his career. He spent years trying to rebuild strength, experimenting with therapies and eventually finding relief and community at Warm Springs. In public, he worked hard to project confidence. The mechanics of appearing before crowds became carefully managed because he could not simply walk into a room as he once had.

Eleanor did not become his nurse and disappear into that role. She supported his political return while continuing to enlarge her own public life. She traveled, organized Democratic women, spoke to groups, cultivated reformers, and gathered information from places Franklin could not easily reach.

This created a marriage with two centers of gravity. Franklin remained the politician with national ambitions. Eleanor increasingly had her own network, her own causes, and her own credibility. Their interests overlapped, but their lives were no longer arranged as one person leading and the other following.

The arrangement solved different problems for each of them. Franklin needed political continuity while rebuilding a public image after paralysis. Eleanor needed a life in which usefulness did not depend on being loved in the way she had once expected. Politics did not heal the marriage, but it gave the couple a language in which cooperation could continue after intimacy had become more complicated.

Val-Kill made that separation visible in physical space. On Roosevelt property near Hyde Park, Eleanor and close friends including Nancy Cook and Marion Dickerman developed a retreat that became central to her independent life. The National Park Service later described Val-Kill as important to her development as a leader in her own right.

The significance was not that Eleanor had found a picturesque cottage. She had found a place where the social rules of the main Roosevelt household did not dominate every hour. Work, friendships, political discussion and experiments such as Val-Kill Industries could exist in a space associated with Eleanor rather than with Sara or Franklin.

Franklin, meanwhile, needed allies who could move. Eleanor could campaign, observe, report and make appearances that helped keep him politically present during years when his physical recovery remained uncertain. The partnership therefore deepened for reasons that had little to do with restored romance.

That distinction matters. It would be easy to romanticize the story by saying the affair made Eleanor stronger and Franklin's disability brought them back together. The evidence is more complicated. Eleanor's independence grew through pain and work, not through a neat lesson. Franklin benefited from that independence even though the marriage still contained secrets and unresolved injuries.

By the time Franklin returned to elected office as governor of New York and then won the presidency in 1932, the arrangement was mature. The White House did not transform a conventional couple into something unusual. It exposed an unusual marriage that had already been evolving for more than a decade.
""",
    },
    {
        "group": "white-house-strange-marriage",
        "purpose": "Use public power as evidence of the unusual marriage, not as a policy lecture.",
        "priority": "must_real",
        "queries": [
            "Eleanor Roosevelt White House press conference women reporters archival",
            "Eleanor Roosevelt travel New Deal projects archival footage",
            "Franklin Eleanor Roosevelt White House archival footage 1930s",
        ],
        "refs": [SOURCES["eleanor"], SOURCES["anderson"], SOURCES["fdr"]],
        "visual": "Authentic White House-era footage and stills of Eleanor traveling, speaking, writing and meeting citizens alongside Franklin's presidential imagery; policy context only when it shows their different roles.",
        "text": """
When Franklin and Eleanor entered the White House in 1933, Americans saw a president and First Lady. Privately, they were also two political operators linked by marriage but not confined to the same circle. Eleanor traveled constantly, held press conferences for women reporters, wrote, spoke, inspected projects, met activists, and returned with information that did not always pass through presidential staff.

The phrase later used for her role—Franklin's “eyes and ears”—is useful only if the second half is remembered. Eyes and ears can report things the person in power would rather not see or hear. Eleanor did not simply confirm Franklin's worldview. She pressed him, embarrassed him, disagreed with him, and associated with people whose demands were often politically inconvenient.

That friction was part of the marriage. Eleanor had access no ordinary activist possessed because she could speak to the president as his spouse. Yet she also had standing outside his staff because her public identity was no longer entirely borrowed from him. The very distance that made their private life unconventional made her harder to control politically.

At the end of a day, this could produce a strange form of intimacy. Eleanor might return from a trip with complaints from workers, young people or Black activists and carry those observations directly into the president's private world. She was not filing a neutral field report. She was using the one relationship that could bypass layers of staff while also speaking from a political identity Franklin had not designed.

The Marian Anderson controversy in 1939 shows the pattern without requiring a lecture on the entire New Deal. When the Daughters of the American Revolution denied Anderson the use of Constitution Hall because of racial restrictions, Eleanor resigned from the organization. Her public decision intensified attention around the case. The administration later approved Anderson's Easter Sunday concert at the Lincoln Memorial.

Eleanor's action did not mean she controlled Franklin's civil-rights policy. She did not. Franklin was balancing a political coalition that included segregationist southern Democrats, and the administration repeatedly compromised in ways Eleanor disliked. Her influence was real precisely because it had limits: she could create pressure inside the family without being able to command the president.

The same pattern repeated across travel, relief programs, labor questions, youth programs and wartime concerns. Eleanor went somewhere, listened to people, came back with an argument, and forced an issue closer to Franklin's desk. Sometimes he acted. Sometimes he did not. Sometimes they disagreed sharply.

This is why their marriage cannot be understood as a public shell covering two completely separate lives. They were separate in many emotional and social ways, but politically they kept crossing into each other's work. Eleanor's independence gave Franklin information and constituencies he did not naturally possess. Franklin's presidency gave Eleanor a platform that no reform organization could have manufactured for her.

Neither side of that exchange should be exaggerated. Eleanor did not secretly run the presidency, and Franklin did not create her beliefs for her. What they created was a channel: sometimes cooperative, sometimes argumentative, occasionally ignored, but almost impossible for an ordinary adviser to reproduce. The spouse who had once been expected to support a rising politician had become one of the few people close enough to challenge him without becoming his employee.

The bargain had benefits for both of them. It also made secrecy easier. Two people with separate schedules, separate confidants and separate emotional worlds could remain politically connected while knowing far less about each other's private lives than the public assumed.
""",
    },
    {
        "group": "lucy-returns",
        "purpose": "Bring the original secret back before the death scene and increase tension.",
        "priority": "must_real",
        "queries": [
            "Lucy Mercer Rutherfurd later life portrait",
            "Anna Roosevelt Halsted Franklin Roosevelt 1944 archival",
            "Franklin Roosevelt Lucy Mercer Rutherfurd 1940s Warm Springs",
        ],
        "refs": [SOURCES["mercer"], SOURCES["fdr"]],
        "visual": "Lucy Mercer Rutherfurd later-life portraits, Anna Roosevelt Halsted, Franklin in the early 1940s and Warm Springs; avoid invented secret-meeting imagery when authentic material is unavailable.",
        "text": """
And then Lucy Mercer came back.

After the 1918 crisis, Lucy married Winthrop Rutherfurd and built a life outside the Roosevelt household. The promise that had helped keep Franklin's marriage intact was that his relationship with her would end. But later contact resumed. The surviving record does not let historians reconstruct every meeting or private emotion, and it would be dishonest to pretend it does. What is clear is that Lucy again became part of Franklin's private world.

Eleanor did not know the full extent of that renewed contact. Their daughter Anna did. By the final years of Franklin's life, Anna was one of the people closest to her father and helped arrange meetings between him and Lucy. That placed the daughter inside the oldest fracture in her parents' marriage.

For Anna, the choice was its own loyalty problem. Franklin was an aging father carrying the pressures of war and declining health. Eleanor was the mother who had been wounded by the same relationship decades before. Helping one parent protect a private companionship meant helping conceal it from the other. The old affair had become a family secret with a second generation of participants.

Think about the arrangement for a moment. Franklin and Eleanor were still appearing as the nation's presidential couple. Eleanor was traveling, writing and advocating. Franklin was leading a global war. Their public partnership was functioning at the highest level of power. At the same time, a private relationship that had almost ended the marriage in 1918 was being maintained behind Eleanor's back.

The secrecy did not require Franklin and Eleanor to hate each other. That is what makes it more unsettling. A marriage can contain loyalty in one domain and deception in another. Franklin could value Eleanor as a political partner, trust her judgment on some questions, depend on her public work, and still hide Lucy from her.

By 1944, Franklin's health was deteriorating. He won a fourth term, but people close to him could see how much the presidency and the war had taken from him. In March 1945 he went to Warm Springs to rest. Lucy was among the people invited into that final private circle.

The story was now moving back toward the place where it began—not geographically, but emotionally. The woman whose letters Eleanor had found in 1918 was again close to Franklin. The difference was that this time Eleanor would learn the truth only after there was no husband left to confront.
""",
    },
    {
        "group": "death-and-second-betrayal",
        "purpose": "Pay off the cold open with Eleanor's discovery and family consequences.",
        "priority": "must_real",
        "queries": [
            "Eleanor Roosevelt April 1945 Franklin death archival",
            "Franklin Roosevelt funeral train 1945 Eleanor archival",
            "Little White House Warm Springs unfinished portrait 1945",
        ],
        "refs": [SOURCES["mercer"], SOURCES["fdr"], SOURCES["eleanor"]],
        "visual": "Warm Springs, Shoumatoff unfinished portrait, Eleanor in April 1945, funeral train and Hyde Park burial; use authentic photographs and newsreel footage.",
        "text": """
On April 12, Roosevelt posed while Elizabeth Shoumatoff worked. Lucy Mercer Rutherfurd was present at Warm Springs. Franklin collapsed, and the emergency became fatal. Lucy left before Eleanor arrived.

For Eleanor, the revelation landed on top of grief. She had lost the man who had been her husband for forty years and the political partner whose rise had become inseparable from her own public life. Now she also had to absorb the fact that Lucy had remained in the story after all.

There was no time for a private reckoning with Franklin. That may be the cruelest difference between 1918 and 1945. After the letters, Eleanor could confront him, offer divorce and negotiate what came next. After Warm Springs, she received information with no possibility of explanation from the man who had kept it from her. Death turned an old marital dispute into a permanent unanswered question.

Anna's role made the discovery more painful. This was no longer only a secret between husband and former lover; it had entered the family. Eleanor and Anna would continue to have a relationship, but the episode revealed how many private accommodations had accumulated around Franklin during the final years.

The funeral train carried Roosevelt's body north from Georgia as Americans gathered along the tracks. Public mourning turned Franklin into a national symbol almost instantly. Eleanor had no such luxury of simplicity. She knew the symbol, the president, the father of her children, the political ally and the man who had deceived her were the same person.

That is why the Warm Springs scene matters more than gossip. It proves that the Roosevelt marriage never resolved into an easy moral ending. They had built a partnership strong enough to survive illness, campaigns, the White House, depression and war. It was not strong enough to make all the old secrets disappear.

Yet Franklin's death also revealed something else. Eleanor no longer needed the marriage in order to have a public identity. The life she had built inside the space created after 1918 was now capable of continuing without him.
""",
    },
    {
        "group": "eleanor-after-franklin",
        "purpose": "Show political power as the consequence of the changed marriage, not the middle of the story.",
        "priority": "must_real",
        "queries": [
            "Eleanor Roosevelt United Nations 1946 archival footage",
            "Eleanor Roosevelt Universal Declaration Human Rights 1948 archival",
            "Eleanor Roosevelt Val-Kill later years archival",
        ],
        "refs": [SOURCES["eleanor"], SOURCES["valkill"], SOURCES["udhr"]],
        "visual": "Authentic post-1945 Eleanor Roosevelt at Val-Kill, United Nations sessions and human-rights work, with international drafting-team imagery when discussing the UDHR.",
        "text": """
Within a year, President Harry Truman appointed Eleanor Roosevelt a United States delegate to the newly created United Nations. That appointment is sometimes presented as a grand final chapter added after the Roosevelt presidency. In this story, it is evidence of what had already happened to her.

Eleanor arrived at the United Nations with decades of practice operating around power without holding the highest office herself. She knew how to build alliances, use publicity, chair meetings, press an argument, accept partial victories and continue after losing a private fight. Those habits had been formed in party organizations, reform networks, the White House—and in a marriage where influence rarely meant control.

She became the first chair of the UN Commission on Human Rights and chaired the process that produced the Universal Declaration of Human Rights. She was not its sole author. The drafting effort was international, with major contributions from figures including P. C. Chang, Charles Malik, René Cassin, John Humphrey, Hansa Mehta and others.

The declaration was adopted on December 10, 1948. It did not erase the contradictions of Eleanor's earlier life or of Franklin's administration. It did prove that the public identity she had built was durable. Franklin's death had removed the presidency from her daily life, but it had not removed her ability to matter politically.

Val-Kill became the clearest symbol of that independence. It was a home associated with Eleanor's own network, visitors, work and choices. The young wife who once lived inside a household heavily shaped by Sara Roosevelt had become a former First Lady whose political life no longer depended on residing in anyone else's house.

This is the payoff to the question of 1918. Eleanor stayed in the marriage, but she did not stay in the same position. The private rupture did not automatically empower her; years of work did that. What the rupture changed was the structure. It gave her fewer reasons to confuse marital unity with personal identity and more room to construct a life that could survive the marriage itself.

That is a more demanding interpretation than the slogan that betrayal made her stronger. Betrayal is not a training program. Eleanor's strength came from what she built afterward: political skill, friendships, work habits, public credibility, and a willingness to keep acting even when the people closest to her disappointed her. The affair is important because it changed the conditions under which that work unfolded.
""",
    },
    {
        "group": "what-the-marriage-became",
        "purpose": "Resolve the mystery without turning betrayal into a simplistic empowerment myth.",
        "priority": "prefer_real",
        "queries": [
            "Franklin Eleanor Roosevelt together archival photographs",
            "Eleanor Roosevelt Franklin Roosevelt family White House archival",
            "Eleanor Roosevelt Val-Kill Franklin Roosevelt memorial archival",
        ],
        "refs": [SOURCES["eleanor"], SOURCES["fdr"], SOURCES["miller"]],
        "visual": "Authentic photographs of Franklin and Eleanor across different decades, family and White House images, then Eleanor alone at Val-Kill; repeat earlier verified portraits deliberately as visual callbacks.",
        "text": """
It is tempting to force the Roosevelt marriage into a familiar category. A great love story. A sham marriage. A betrayed wife who transformed pain into greatness. A powerful man forgiven because history remembers his achievements. None of those versions can hold all the evidence.

Franklin and Eleanor remained connected by children, affection, history, ambition, public duty and genuine political usefulness. They also maintained separate friendships, separate spaces and secrets. Eleanor could defend Franklin's legacy and still be wounded by what happened at Warm Springs. Franklin could rely on Eleanor's independence and still conceal Lucy from her.

The marriage survived because it changed form. That does not mean the change was fair. Eleanor did not choose the betrayal that forced the first break, and the later secrecy repeated the injury. Their children were pulled into adult arrangements they had not created. None of that should be romanticized as the price of greatness.

Staying, then, was not the same thing as surrender. It preserved a family and a political partnership, but it also gave Eleanor years in which to redraw the boundaries of her own life from inside the arrangement. The result was full of compromise. It was also very different from the dependent young marriage Sara Roosevelt had once been able to supervise through a connecting door.

But the political consequence is impossible to ignore. Eleanor became influential partly because she was close enough to power to reach Franklin and independent enough to disagree with him. The White House gave her reach; the distance inside the marriage gave her room to develop a voice that was not simply his.

Franklin benefited from the same arrangement. He had a spouse who could travel when his body made travel harder, speak to constituencies outside his immediate circle, bring uncomfortable information into the presidency and campaign with credibility of her own. Their differences were not merely tolerated. At times, those differences made the partnership useful.

Return to the last portrait at Warm Springs. The image freezes Franklin at the end of his life, but the people outside the frame tell the larger story. Lucy was there. Eleanor was not. Anna knew more than her mother. The president's private world and public world had separated one final time.

And still, that is not the ending. Eleanor continued for seventeen more years, writing, traveling, organizing and arguing in public. The marriage that had once defined the boundaries of her life became one part of a much larger identity.

The secret behind the familiar Roosevelt photographs is not that Franklin and Eleanor conquered betrayal and restored a perfect marriage. They never did. The more revealing truth is that they learned to operate inside a broken one—and Eleanor gradually built enough independent power that the marriage could break again at the very end without breaking her with it.
""",
    },
]


RESEARCH = f"""# Research

## Chosen angle
**The Marriage That Changed Shape: Why Eleanor Roosevelt Stayed After Franklin's Affair—and What Their Strange Partnership Became**

The story is relationship-first. The central mystery is not a broad survey of Eleanor Roosevelt's politics; it is why she remained married after discovering Franklin Roosevelt's relationship with Lucy Mercer in 1918, how the marriage changed afterward, why Lucy returned to Franklin's private life, and what Eleanor's later independence reveals about the bargain she made by staying.

## Audience promise
Open on April 12, 1945 at Warm Springs: Franklin dies while Lucy Mercer Rutherfurd is again inside his private circle. Then move backward to the 1918 letters and forward through the changed marriage. Public history appears only when it changes the relationship or proves what the new arrangement allowed Eleanor and Franklin to become.

## Narrative reference analysis — American Secrets
Four reference scripts were reviewed: Donald Trump's parents (D42lCZtHHv4), Ivanka Trump's marriage (xrneEs9VKBU), Jackie Kennedy/JFK (C-OUHTFbiE8), and Ethel Kennedy (wwOAXHL57RY). The reusable pattern is third-person documentary narration with sparse direct-address pivots; a concrete scene/date/photo/object in the cold open; an early contradiction; then a human relationship or family mystery that stays open across the video. Dates, money, legal records, letters, funerals and photographs are used as evidence inside the private conflict rather than as a detached history lecture. This production adopts that narrative logic without copying wording or channel identity.

## Relationship spine
1. Warm Springs, 1945 — Lucy is present when Franklin dies.
2. Before Lucy — marriage, family dependence and the cost of divorce.
3. 1918 — Eleanor finds Lucy's letters and offers divorce.
4. Why she stays — children, family/financial/political/social pressures and a bond too complex to reduce to one motive.
5. The marriage changes form — Eleanor builds independent networks; Franklin's 1921 illness makes her mobility politically valuable.
6. White House years — use policy/civil-rights examples only to show their two-center partnership and disagreement.
7. Lucy returns — Anna helps arrange meetings Eleanor does not fully know about.
8. Franklin dies — the old secret is exposed again.
9. Eleanor afterward — UN/UDHR is payoff proving her identity survived the marriage, not the dominant middle act.

## Core verified claims and safeguards
- Franklin and Eleanor married March 17, 1905 and had six children, one dying in infancy.
- Eleanor discovered Franklin's relationship with Lucy Mercer in 1918 after finding letters in Franklin's luggage. Divorce was discussed; the marriage continued amid family, financial, social and political pressures.
- The post-1918 relationship is described by institutional/biographical sources as a durable partnership that became less conventionally intimate and gave Eleanor increasing independence.
- Franklin suffered paralytic illness in 1921, historically diagnosed as polio, and never again walked unaided.
- Val-Kill became an important base for Eleanor's independent life and political development.
- As First Lady, Eleanor traveled, reported conditions, wrote, held press conferences and pressed causes independently; influence must not be confused with control of Franklin.
- In 1939 Eleanor resigned from the DAR after Marian Anderson was denied Constitution Hall; the later Lincoln Memorial concert is used only as a concise example of her independent pressure.
- Lucy Mercer Rutherfurd later re-entered Franklin's life. Eleanor did not know the full extent of later meetings and was disturbed to learn Lucy had been present when Franklin died at Warm Springs on April 12, 1945.
- Truman appointed Eleanor a U.S. delegate to the United Nations in 1946. She chaired the UN Commission on Human Rights and the UDHR drafting process; she was one leader among an international drafting team, not the sole author.

## Institutional sources
- Eleanor Roosevelt Papers Project — Lucy Page Mercer Rutherfurd: {SOURCES['mercer']}
- Eleanor Roosevelt Papers Project — Franklin Delano Roosevelt: {SOURCES['fdr']}
- Eleanor Roosevelt Papers Project — Short Biography of Eleanor Roosevelt: {SOURCES['eleanor']}
- National Park Service — Val-Kill: {SOURCES['valkill']}
- FDR Presidential Library — Eleanor Roosevelt and Marian Anderson: {SOURCES['anderson']}
- Miller Center — FDR Family Life: {SOURCES['miller']}
- United Nations — Drafters of the Universal Declaration: {SOURCES['udhr']}

## Wording safeguards
Do not pretend Eleanor's private motives are fully knowable. Do not assign sexual labels to private friendships without adequate evidence. Do not present Eleanor as controlling Franklin's policy, or as the sole author of the UDHR. Do not frame Franklin's betrayal as a necessary or beneficial cause of Eleanor's achievements; distinguish the injury from the work Eleanor herself did afterward.
"""


def _sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.strip())
    if not normalized:
        return []
    return [piece.strip() for piece in re.split(r"(?<=[.!?])\s+", normalized) if piece.strip()]


def _split_sentence(sentence: str, max_words: int = 25) -> list[str]:
    words = sentence.split()
    if len(words) <= max_words:
        return [sentence]
    chunks: list[str] = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if len(current) >= 18 and (word.endswith(",") or word.endswith(";") or word.endswith(":")):
            chunks.append(" ".join(current))
            current = []
        elif len(current) >= max_words:
            chunks.append(" ".join(current))
            current = []
    if current:
        if chunks and len(current) < 8:
            chunks[-1] = f"{chunks[-1]} {' '.join(current)}"
        else:
            chunks.append(" ".join(current))
    return chunks


def _beat_chunks(text: str) -> list[str]:
    pieces: list[str] = []
    for sentence in _sentences(text):
        pieces.extend(_split_sentence(sentence))
    combined: list[str] = []
    current = ""
    for piece in pieces:
        if not current:
            current = piece
            continue
        current_words = len(current.split())
        piece_words = len(piece.split())
        if (current_words < 10 or piece_words < 8) and current_words + piece_words <= 26:
            current = f"{current} {piece}"
            continue
        combined.append(current)
        current = piece
    if current:
        combined.append(current)
    return combined


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    paragraphs: list[str] = []
    beats: list[dict[str, object]] = []
    beat_index = 1
    for section in SECTIONS:
        section_paragraphs = [p.strip() for p in section["text"].strip().split("\n\n") if p.strip()]
        paragraphs.extend(section_paragraphs)
        chunks = _beat_chunks(section["text"])
        for local_index, chunk in enumerate(chunks):
            beat_id = f"B{beat_index:03d}"
            on_screen_text = ""
            if local_index == 0:
                if section["group"] == "warm-springs-secret-revealed":
                    on_screen_text = "WARM SPRINGS · APRIL 12, 1945"
                elif section["group"] == "affair-discovery-1918":
                    on_screen_text = "1918"
                elif section["group"] == "death-and-second-betrayal":
                    on_screen_text = "APRIL 12, 1945"
            beats.append({
                "beat_id": beat_id,
                "story_group": section["group"],
                "narration_text": chunk,
                "purpose": section["purpose"],
                "target_duration_sec": 0.0,
                "visual_type": "sourced_video",
                "source_priority": section["priority"],
                "visual_description": f"{section['visual']} Current spoken beat: {chunk}",
                "footage_search_queries": section["queries"],
                "factual_source_refs": section["refs"],
                "framing_motion_intent": "Prefer authentic archival video first, then authentic stills. One verified asset may cover adjacent beats in this story_group when context remains correct; vary crop, pan, push-in, detail framing or source time range instead of forcing sentence-literal replacement.",
                "on_screen_text": on_screen_text,
                "sound_notes": "Restrained archival ambience/music bed; use emphasis only for reveal or reversal, not on every beat.",
            })
            beat_index += 1

    script = "\n\n".join(paragraphs).strip() + "\n"
    total_words = len(re.findall(r"\b[\w’'-]+\b", script))
    raw_durations = [max(4.5, min(9.5, len(str(beat["narration_text"]).split()) * 0.42)) for beat in beats]
    scale = 1800.0 / sum(raw_durations)
    running = 0.0
    for index, (beat, raw) in enumerate(zip(beats, raw_durations)):
        duration = round(raw * scale, 3)
        if index == len(beats) - 1:
            duration = round(1800.0 - running, 3)
        beat["target_duration_sec"] = duration
        running += duration

    manifest = {
        "target_duration_sec": 1800,
        "beats": beats,
        "narrative_strategy": {
            "default_pov": "third_person_documentary",
            "direct_address": "sparse_hook_only",
            "spine": [
                "affair",
                "discovery",
                "why_she_stayed",
                "strange_marriage",
                "lucy_returns",
                "death_reveals_secret",
                "eleanor_afterward",
            ],
            "footage_matching": "story_group_context_first_not_sentence_literal",
        },
    }
    (OUT / "research.md").write_text(RESEARCH.strip() + "\n", encoding="utf-8")
    (OUT / "script.md").write_text(script, encoding="utf-8")
    (OUT / "visual_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    stats = {
        "word_count": total_words,
        "beat_count": len(beats),
        "planned_duration_sec": round(sum(float(beat["target_duration_sec"]) for beat in beats), 3),
        "story_groups": list(dict.fromkeys(str(beat["story_group"]) for beat in beats)),
    }
    (OUT / "candidate_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
