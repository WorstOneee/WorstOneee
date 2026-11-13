#!/usr/bin/env python3
import datetime
import html
import json
import os
import urllib.request
from pathlib import Path

USER = "WorstOneee"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ASSETS = Path("assets")
ASSETS.mkdir(exist_ok=True)

def api(url, payload=None):
    headers = {"Accept":"application/vnd.github+json", "User-Agent":"profile-activity"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    data = json.dumps(payload).encode() if payload is not None else None
    if data:
        headers["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=25) as response:
        return json.load(response)

def svg_header(title, subtitle, height):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="900" height="%s" viewBox="0 0 900 %s">'
            '<defs><linearGradient id="background"><stop stop-color="#0b1120"/>'
            '<stop offset="1" stop-color="#102a43"/></linearGradient>'
            '<linearGradient id="neon" x2="0" y2="1"><stop stop-color="#38bdf8"/>'
            '<stop offset="1" stop-color="#0a669f"/></linearGradient></defs>'
            '<rect x="1" y="1" width="898" height="%s" rx="14" fill="url(#background)" stroke="#24618a"/>'
            '<text x="30" y="43" font-family="Arial,Helvetica,sans-serif" font-size="23" font-weight="bold" fill="#e6f6ff">%s</text>'
            '<text x="30" y="66" font-family="Arial,Helvetica,sans-serif" font-size="12" fill="#75c8eb">%s</text>'
            % (height, height, height-2, html.escape(title), html.escape(subtitle)))

def create_stats(profile, repos, year):
    numbers = [
        ("PUBLIC REPOSITORIES", str(profile.get("public_repos", 0))),
        ("TOTAL STARS", str(sum(int(r.get("stargazers_count",0)) for r in repos))),
        ("FOLLOWERS", str(profile.get("followers",0))),
        ("YEARLY CONTRIBUTIONS", str(year) if year is not None else "N/A")
    ]
    result = svg_header("GitHub Stats", "Updated daily via GitHub Actions", 204)
    for i, (label, value) in enumerate(numbers):
        x = 30+i*218
        result += ('<rect x="%d" y="89" width="202" height="88" rx="8" fill="#122c44" stroke="#245777"/>'
                   '<text x="%d" y="115" font-size="11" fill="#96bdd6" font-family="Arial,Helvetica,sans-serif">%s</text>'
                   '<text x="%d" y="153" font-size="32" font-weight="bold" fill="#38bdf8" font-family="Arial,Helvetica,sans-serif">%s</text>'
                   % (x,x+16,html.escape(label),x+16,html.escape(value)))
    (ASSETS/"github-stats.svg").write_text(result+"</svg>",encoding="utf-8")

def create_graph(weekly, title, subtitle):
    result = svg_header(title, subtitle, 240)
    left, right, base, top = 50, 867, 190, 90
    peak = max([1]+weekly)
    for step in range(5):
        y = base - step * 25
        result += '<path d="M%d %d H%d" stroke="#24506e" stroke-opacity=".6"/>' % (left,y,right)
    n = max(len(weekly), 1)
    gap = (right-left)/n
    bw = min(15,gap*.6)
    for i,num in enumerate(weekly):
        h = num/peak*100
        x = left+i*gap+(gap-bw)/2
        result += ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" fill="#38bdf8">'
                   '<title>Week %d: %d</title></rect>' % (x,base-h,bw,max(1,h),i+1,num))
    result += ('<text x="50" y="219" font-size="12" fill="#91bed8" font-family="Arial,Helvetica,sans-serif">Earlier</text>'
               '<text x="866" y="219" font-size="12" text-anchor="end" fill="#91bed8" font-family="Arial,Helvetica,sans-serif">Latest</text></svg>')
    (ASSETS/"github-activity.svg").write_text(result,encoding="utf-8")

def main():
    profile = api("https://api.github.com/users/"+USER)
    repos=[]
    for page in range(1,8):
        batch = api("https://api.github.com/users/%s/repos?type=owner&per_page=100&page=%d"%(USER,page))
        repos.extend(batch)
        if len(batch)<100: break
    yearly = None
    try:
        query = "query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{contributionCount}}}}}}"
        result = api("https://api.github.com/graphql",{"query":query,"variables":{"login":USER}})
        if result.get("errors"):
            raise ValueError(result["errors"])
        cal=result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        weekly=[sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]]
        yearly=cal["totalContributions"]
        graph_title="GitHub Contributions"
        graph_subtitle="Contributions per week · past year · updated daily"
    except Exception as e:
        print("Contributions API fallback:",str(e)[:250])
        today = datetime.datetime.now(datetime.timezone.utc).date()
        weekly = [0]*12
        try:
            for page in range(1,4):
                batch=api("https://api.github.com/users/%s/events/public?per_page=100&page=%d"%(USER,page))
                for event in batch:
                    date=datetime.date.fromisoformat(event["created_at"][:10])
                    idx=11-(today-date).days//7
                    if 0<=idx<12: weekly[idx]+=1
                if len(batch)<100: break
        except Exception as e2:
            print("Public event fallback:",str(e2)[:250])
        graph_title="Public GitHub Activity"
        graph_subtitle="Public events per week · past 12 weeks · updated daily"
    create_stats(profile,repos,yearly)
    create_graph(weekly,graph_title,graph_subtitle)

if __name__=="__main__":
    main()
