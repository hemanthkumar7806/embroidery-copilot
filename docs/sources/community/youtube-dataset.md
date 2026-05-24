# YouTube transcript dataset (community)

- **Source:** YouTube digitizing tutorials. Content extracted from transcripts fetched via **yt-dlp** (terminal) or Transcript API (curl).
- **Collected:** 2026-02-20

**Summary:** This file documents how to fetch YouTube transcripts and where to store extracted content (density, underlay, pull comp, fabric tips, failure causes) so AI can use it without opening videos.

---

## How to fetch a transcript

**Python (requests) – recommended when transcriptapi.com is working:**

```python
import requests

url = "https://transcriptapi.com/api/v2/youtube/transcript?video_url=https://www.youtube.com/watch?v=VIDEO_ID&format=json"
headers = {"Authorization": "Bearer YOUR_API_KEY"}
response = requests.get(url, headers=headers)
data = response.json()
# data["transcript"] is a list of {"text": "...", "start": float, "duration": float}
text = " ".join(seg["text"] for seg in data.get("transcript", []))
```

Do not commit the API key; use an environment variable. To fetch multiple public (non-private) videos, use the script [fetch_transcript_api.py](fetch_transcript_api.py) in this folder (set `TRANSCRIPT_API_KEY`, then run `python fetch_transcript_api.py` or pass video URLs as arguments).

**Curl.** Set `VIDEO` to the full YouTube URL, then run:

```bash
curl -s \
  -H "Authorization: Bearer YOUR_API_KEY" \
  "https://transcriptapi.com/api/v2/youtube/transcript?video_url=$VIDEO&format=json"
```

**Example (PowerShell, use curl.exe to avoid alias):**

```powershell
$VIDEO = "https://www.youtube.com/watch?v=Is5A47QQakI"
curl.exe -s -H "Authorization: Bearer YOUR_API_KEY" "https://transcriptapi.com/api/v2/youtube/transcript?video_url=$VIDEO&format=json"
```

**Example (bash):**

```bash
export VIDEO="https://www.youtube.com/watch?v=Is5A47QQakI"
curl -s \
  -H "Authorization: Bearer YOUR_API_KEY" \
  "https://transcriptapi.com/api/v2/youtube/transcript?video_url=$VIDEO&format=json"
```

The response is JSON. Parse it to get the transcript text (e.g. segments with `text` or similar fields), then extract only the **necessary content**: concrete numbers (density in mm, underlay types, pull comp values), fabric-specific tips, and failure causes. Paste that extracted content into the sections below (or into common-mistakes.md / fabric-presets.md / failure-causes.md) so AI can retrieve it without opening the URL.

**Do not commit the API key.** Use an environment variable (e.g. `TRANSCRIPT_API_KEY`). If the repo is public, add `youtube-transcript-*-api.json` to `.gitignore` to avoid committing raw transcript JSON.

**PowerShell script:** A helper script [fetch-youtube-transcript.ps1](fetch-youtube-transcript.ps1) in this folder fetches a transcript and saves it as `youtube-transcript-<videoId>.json`. Set `$env:TRANSCRIPT_API_KEY` then run: `.\fetch-youtube-transcript.ps1 -VideoUrl "https://www.youtube.com/watch?v=Is5A47QQakI"`. Parse the JSON and paste extracted content into the sections below.

**Alternative: yt-dlp (terminal, no API key):** If the Transcript API fails or the video is public, use yt-dlp to download the transcript from the terminal:

```powershell
cd "e:\user\code\MCP-chatbot\docs\sources\community"
yt-dlp --skip-download --write-subs --write-auto-subs --sub-format json3 --sub-langs en -o "youtube-transcript-%(id)s" "https://www.youtube.com/watch?v=VIDEO_ID"
```

This creates `youtube-transcript-VIDEO_ID.en.json3`. Parse the JSON (extract `events[].segs[].utf8` and concatenate) to get plain text, then extract relevant content and paste below. A plain-text version can be generated with a short script (see `youtube-transcript-3xpLqGkHHQM.txt` in this folder).

---

## Videos to process

| Video | URL | Fetched via | Extracted content |
|-------|-----|-------------|-------------------|
| Push and Pull Compensation (beginners) | https://www.youtube.com/watch?v=Is5A47QQakI | — (private) | § Video 1 — **Note:** Video is private/unavailable; no transcript collected. Pull compensation rules rely on other videos (Video 2, Video 3, Video 4) and community docs (common-mistakes.md, failure-causes.md). |
| FREE Embroidery Digitizing 101 Course | https://www.youtube.com/watch?v=3xpLqGkHHQM | yt-dlp | § Video 2 |
| How to Digitize a Logo for Beginners | https://www.youtube.com/watch?v=Pr_Du4rbxDE | Transcript API (Python requests) | § Video 3; file: youtube-transcript-Pr_Du4rbxDE-api.txt |
| Learn to Digitize for Machine Embroidery | https://www.youtube.com/watch?v=ie9ArCsHtZc | Transcript API | § Video 4; file: youtube-transcript-ie9ArCsHtZc-api.txt |
| Digitizing Line Art – Embrilliance StitchArtist | https://www.youtube.com/watch?v=zwfIuDRhN2k | Transcript API | § Video 5; file: youtube-transcript-zwfIuDRhN2k-api.txt |

Note: Apart from private videos, use **Transcript API** (Python requests or curl with API key) to fetch others. Script: `fetch_transcript_api.py`; outputs `youtube-transcript-VIDEO_ID-api.json` and `youtube-transcript-VIDEO_ID-api.txt`.

---

## Extracted content (Video 1) – Push and Pull Compensation

*After running the curl command and parsing the JSON transcript, paste here only the sentences or segments that contain:*
- *Pull compensation values (mm or %)*
- *Underlay mentions*
- *Density or spacing numbers*
- *Fabric-specific tips*
- *Why designs fail (causes)*

*(Transcript API returned "Request failed, please retry" at collection time; run the curl locally and paste extracted content here.)*

---

## Extracted content (Video 2) – Digitizing 101

**Source:** FREE Embroidery Digitizing 101 Course – Embroidery Legacy (John Deere).  
**URL:** https://www.youtube.com/watch?v=3xpLqGkHHQM  
**Fetched via:** yt-dlp (terminal); transcript saved as `youtube-transcript-3xpLqGkHHQM.en.json3` and `youtube-transcript-3xpLqGkHHQM.txt`.

**Content from transcript (extracted for density, underlay, pull comp, fabric, stitch length, failure causes):**

- **Stitch length (running):** “The minimum stitch length I would ever want to create on an embroidery machine is 0.5 mm. If you go below that the machine can think it’s stitching in the same place and create thread breaks. Move up a little from there to 1 mm. And 1 mm is kind of the safe zone. 0.5 mm as the red zone, 1 mm as the orange zone, and then I can go up to 1.5 as the green zone. Most of my stitch penetrations are at least a millimeter to a millimeter and a half apart from each other.”
- **Satin stitch length / width:** “You want to make sure you don’t overstep the rules of how long the stitch becomes. I wouldn’t want to try to do a stitch 0.5 mm in width because it will sink into the fabric and disappear. So I always try to have at least 1 mm of space between the stitches going back and forth. On some fabrics a 1 mm stitch will still disappear, like if you’re embroidering on terry cloth or sherpa. So about 1.5 mm is usually within the safety zone. And again you can go up to 5 to 7 mm for a wearable item and 7 to 12 mm for a non-wearable item.”
- **Density:** “Density is basically the space between each stitch. And that space does vary depending on a few factors. The normal density that we use is just a little bit larger than the width of a thread, so it looks like you have full coverage when it’s embroidered on a garment. But sometimes you might need more or less density in a design. And that really depends on the fabric type. If you’re embroidering on vinyl or leather, you’ll need less density in that design because too many penetrations will literally cut through the leather or the vinyl. If you have something like sherpa fleece or terry cloth, you’d actually need more density because there’s such a high pile that you’ll need to add a little bit more to cover the fabric.”
- **Density (layers):** “So many people when they’re learning how to digitize just go with the 0.4 default density and they never change it. They start digitizing layer upon layer on top of each other with the same density and you’re putting full coverage on full coverage. All it’s going to do is create a bulletproof design. As you start building up the layers or colors within your embroidery design, you want to start reducing the density of each layer that you’re building upon. Because embroidery should be soft and flexible, feeling like it’s part of the fabric, not feeling like it’s stiff or glued onto the garment.”
- **Underlay:** “Understanding underlay is one of the most important things to know as a digitizer because underlay is one of those things that you don’t see, but it plays the most important role. It’s laying a foundation within the embroidery design. There are many different types of underlay: center run underlay, edge run, zigzag or double zigzags, zigzags with edge runs to combine underlays. You might need a center run underlay if the satin stitch is very thin. And as that satin stitch gets wider, you might need a zigzag or you might need an edge run to create a break wall. All of them work together to provide a stable foundation for your stitches. The idea behind underlay is that it secures the area underneath the stitches and acts as a break wall to help the visual stitches look clean. Underlays for fill stitches usually run the opposite direction of the fill. They secure the fabric first and provide a foundation for the fill to sit on, which reduces distortion within the design.”
- **Distortion / pull compensation:** “Understanding distortion can be one of the most difficult things for new digitizers. They see their designs on a computer screen and it looks absolutely perfect and then they run it on their machines and they don’t see the same results. The main reason is the pull of the thread as it’s going in and out of the machine and that’s called pull compensation. The wider the stitch, the more it pulls in. And the pull compensation is something that is built into the software program. You can adjust the amount of pull compensation within a design based on the width of the stitch as well as the fabric type.”
- **Registration / pathing:** “Incorrect registration has all kinds of areas where the running stitch is not lining up to the satin or fill areas. Improper use of underlay can play a factor, but this is most often linked to not pathing or mapping your design properly. Every design should be carefully planned out. When a digitizer knows what they’re doing, they know how to look at all the objects and figure out the best and most efficient way to create machine-friendly designs.”
- **Trims:** “Unnecessary trims are one of the worst culprits in embroidery. If you have a design that has 100 unnecessary trims, at every trim it’s approximately 120 stitches, which means that if you have 100 unnecessary trims in a design, that’s like adding 12,000 stitches of lost production time. So trims do matter.”
- **Course outline (topics):** “What is digitizing? The three main stitch types and when to use them, how density affects your stitch outs, what underlay does and why it matters, why designs distort and how to fix them, understanding registration pathing or mapping and fabric recipes.”
- **Machine limit:** “The trimmers will automatically activate if they see a stitch length over 12.1 mm.”

---

## Extracted content (Video 3) – How to Digitize a Logo for Beginners

**Source:** Embroidery Legacy. **URL:** https://www.youtube.com/watch?v=Pr_Du4rbxDE  
**Fetched via:** Transcript API (Python requests). **Files:** youtube-transcript-Pr_Du4rbxDE-api.json, youtube-transcript-Pr_Du4rbxDE-api.txt

**Content from transcript (excerpts):** Recipes (cotton default, pknit for golf shirt, cap for hat); “underlay pull compensation” set by recipe; “2.5 mm run” default; “exaggerate the pull compensation” at open ends; zigzag + edge run underlay for pknit; “edge run only” for some thin areas (no zigzag); “split stitch” over 7 mm; left chest “3 to 4 in” typical, “2 and 1/2 in” for smaller; cap recipe has less pull comp than pknit; varsity cap (no laminated buck) may need cotton recipe or “cap varsity”; “smart join” to avoid unnecessary trims; “slow redraw” to catch errors.

---

## Extracted content (Video 4) – Learn to Digitize for Machine Embroidery

**Source:** YouTube (Embird user). **URL:** https://www.youtube.com/watch?v=ie9ArCsHtZc  
**Fetched via:** Transcript API. **Files:** youtube-transcript-ie9ArCsHtZc-api.txt

**Content from transcript (excerpts):** Four things to avoid: gaping, distortion, very dense, overlapping, puckering (stabilization + digitizing). Build design from objects (like layers); start at back of image, work forward. Use cutout tool so stitches are not stacked (e.g. eye inside fish body): stitch onto material, not on top of embroidery → less density, less pull/strain → less gaping and puckering. When layering fills: if both at 90° the lower color shows through; change stitch angle of the top object (alternating angles). Alternating stitch angles also evens out stretch and reduces gapping/distortion. Reduce trims by connecting objects of same color (connect tool for route control). Pull compensation: at edges of fill or satin, “adjusts the stitch length to make it a little bit longer to kind of knit together with the object next to it”; increase for all objects so they knit together. Summary: adjust pull comp, connect same-color objects to reduce trims, use alternating stitch angles, avoid stacking stitches where possible. Substrate: craft felt, two layers medium-weight tear-away; cotton drill + heat knife for close patch edge.

---

## Extracted content (Video 5) – Digitizing Line Art (Embrilliance StitchArtist)

**Source:** designsbybe.com (Melissa). **URL:** https://www.youtube.com/watch?v=zwfIuDRhN2k  
**Fetched via:** Transcript API. **Files:** youtube-transcript-zwfIuDRhN2k-api.txt

**Content from transcript (excerpts):** Line art = running/bean stitches; StitchArtist Level 1 sufficient. Place nodes only where the stitch changes direction or moves—not “a thousand nodes for every line.” Node types: curve (same amount each way), cusp (sides can go opposite directions), line (straight to next node). Bean stitch length: 2.4–2.5 mm “is fine”; above 2.6 mm → “a lot of variation” (shorter lines stitch shorter, longer ones longer) → uneven / not uniform; some use 2.0. Minimize jump stitches: set tie at entry/exit, reorder objects (move first), align start/end points so “red dashed lines” (jump stitches) disappear; “eliminate as many red dashed lines as possible.” Tip: change color of already-ordered sections (e.g. hot pink) to see what’s connected and what still needs pathing. Line art is “way more about your creative vision and taste than the digitizing”; only need to know how to digitize a line (nodes, curve/cusp/line). Hair: a few lines to suggest hair, not every strand (avoids cluttered look).

---

## Extracted content (other videos)

*Add more video titles and paste extracted transcript content below as you process them.*

---

## URL → topic file mapping (YouTube)

| Video / channel | Extracted content goes to |
|-----------------|----------------------------|
| Pull comp, underlay, density | common-mistakes.md, fabric-presets.md, failure-causes.md |
| Fabric-specific tips from transcript | fabric-presets.md § All fabric types / Density by fabric |
| Failure causes from transcript | failure-causes.md |
| Numeric rules from transcript | community-summary.md § 1. Numeric rules |

After extracting, add the video URL to [community-summary.md](community-summary.md) § 4. URL → file mapping.
