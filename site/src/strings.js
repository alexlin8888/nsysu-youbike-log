// Every word the page shows, in both languages. {x} marks a value filled in by app.js.
var T = {
  zh: {
    docTitle: "Beat the Bell｜中山大學 YouBike", where: "中山大學 YouBike",
    live: "即時", replay: "重播", tabRider: "借車", tabDock: "還車", tabOps: "調度", tabAbout: "說明",
    loading: "讀取資料中", liveAt: "{t} 更新", ago: "{m} 分鐘前", agoH: "{h} 小時前", justNow: "剛剛", replayAt: "重播 {d} {t}",
    stale: "讀不到新資料，先顯示 {t} 那一筆。",
    stalebig: "紀錄器已經 {m} 分鐘沒有新資料，畫面是最後一筆。",
    loadFail: "資料讀不進來（{e}）。請重新整理，或過幾分鐘再試。",
    replayFail: "這一天的重播讀不進來（{e}）。",

    bellNext: "下一次下課", bellIn: "還有 {m} 分", bellInH: "還有 {h} 小時 {m} 分", inMin: "{m} 分", inHour: "{h} 小時 {m} 分", nowIs: "現在 {t}",
    offdayBig: "今天沒課", offdayNote: "假日沒有下課人潮", overBig: "今天下課了", overNote: "最後一堂在 {t} 下課",
    stBikeOk: "校內現在好借", stBikeLow: "校內的車變少了", stBikeOut: "校內現在很難借到車",
    stDockOk: "校內現在好還", stDockLow: "校內的空位變少了", stDockOut: "校內現在很難還車",

    search: "搜尋站名，例如 圖資", noMatch: "找不到這個站",
    originK: "從哪裡", destK: "到哪裡", goalK: "到哪裡", toNone: "不指定", grpCampus: "校內", grpTown: "校外", grpOther: "其他", oMe: "我的位置", oPick: "在地圖上選",
    whenBikeK: "幾點走", whenDockK: "幾點到", wNow: "現在", wBell: "{t} 下課", wPlus: "{m} 分後",
    geoFail: "拿不到你的位置，改用地圖選點", tooFar: "你不在中山附近，位置先留在校園。", picking: "在地圖上點一下，設成起點", pickingDest: "在地圖上點一下，設成目的地", fabLabel: "用我的位置",
    bestBikeNow: "現在去這站借", bestBikeBell: "{t} 下課後去這站借", bestDock: "騎到這站還",
    skipBike: "{n}比較近，但你到的時候很可能沒車", skipDock: "{n}比較近，但你到的時候很可能停滿",
    weakBike: "附近都不一定有車。", weakDock: "附近都不一定有位子。",
    noneBike: "2 公里內沒有站回報資料", noneDock: "目的地附近沒有站回報資料",
    expect: "到時約剩 {b} 台", docksNow: "現在 {d} 個空位", docksNow1: "現在 1 個空位", bikesNow: "現在 {b} 台",
    tipSoon: "{t} 前出發，約 {a} 分鐘內騎上車。{u} 出發約 {b} 分鐘。", tipCalm: "接下來一小時出發，約 {a} 分鐘內騎上車。", 
    relayTag: "+5 元", relayRetHere: "這一站你到的時候約 {o} 成還是空站，把車還在這裡可拿 5 元騎乘券。", relayRetAlt: "{n}你到的時候約 {o} 成還是空站，還到那裡可拿 5 元騎乘券，多花約 {m} 分鐘。",
    relayBorHere: "這一站你到的時候約 {o} 成還是滿站，從這裡借車可拿 5 元騎乘券。", relayBorAlt: "{n}你到的時候約 {o} 成還是滿站，從那裡借車可拿 5 元騎乘券，多走約 {m} 分鐘。",
    relayCardRet: "你到的時候約 {o} 成還是空站，把一般車還在這裡可拿 5 元騎乘券。", relayCardBor: "你到的時候約 {o} 成還是滿站，從這裡借車可拿 5 元騎乘券。",
    aboutRelay: "<h3>「+5 元」是什麼</h3><p>高雄 YouBike 從 2026 年 7 月起有「友愛接力」：在滿站借車，或把一般車還到空站，各送 5 元騎乘券，每天 06:00 到 24:00。符不符合，看的是你借車或還車那一刻的站況。官方 App 顯示現在哪一站空、哪一站滿，這個頁面標出你到的時候很可能還是空站或滿站的地方。拿 12 個上課日來對，標出來的站 10 分鐘後有七成確實還是空的，只看現在是空站的是六成五。實際有沒有拿到以官方紀錄為準。</p>",
    odds: "機會約 {n} 成", tipOn: "沒車的話，再走 {m} 分鐘到{n}。", tipOnDock: "停滿的話，再騎 {m} 分鐘到{n}。", tipSure: "想穩一點可以去{n}，走 {m} 分鐘。", tipSureDock: "想穩一點可以還{n}，還完走 {m} 分鐘。",
    walkWins: "直接走比較快", walkAll: "走路 {m} 分鐘", walkVs: "借車再騎過去約 {m} 分鐘", tripRide: "借車、騎過去、還車，全程約 {a} 分鐘。走路要 {b} 分鐘。",
    laterH: "幾點走，幾分鐘騎得上車", laterSub: "預估，單位是分鐘", nearFresh: "車數是 {t} 的即時數字",
    fav: "我的站", near: "附近的站", nearBike: "顏色是你走到時的狀況", nearDock: "顏色是你騎到時的狀況", more: "再看 8 站", less: "收起來",
    walkK: "步行", walkDest: "到目的地", walkMin: "{m} 分", farK: "直線", walkKm: "{k} 公里",
    cBikeYes: "應該有車", cBikeMaybe: "不一定有車", cBikeNo: "很可能沒車", sGone: "現在沒車",
    cDockYes: "應該有位子", cDockMaybe: "不一定有位子", cDockNo: "很可能停滿", sFullNow: "現在停滿", sNone: "沒有資料", sOos: "暫停服務",
    tGone: "預估 {t} 借光", tKeep: "到 {t} 都有車", tBack: "預估 {t} 有車還回來", tNoBack: "{t} 前大概都沒車",
    tFull: "預估 {t} 停滿", tFree: "到 {t} 都有位子", tOpen: "預估 {t} 有空位", tNoOpen: "{t} 前大概都沒位子",
    usualBikeCampus: "校內平常幾點難借", usualDockCampus: "校內平常幾點難還", usualBikeGate: "這一帶平常幾點難借", usualDockGate: "這一帶平常幾點難還",
    usualTeach: "上課日平均", usualOff: "假日平均", usualPeak: "最難的時段 {a} 到 {b}", usualEasy: "整天都不難",

    fBikes: "可借", fDocks: "可還", fArrive: "你到的時候", aheadH: "接下來 90 分鐘", aheadBike: "預估車數", aheadDock: "預估空位",
    chartCap: "今天的車數。直的虛線是下課鐘，橫的虛線是預估。", addFav: "加入我的站", rmFav: "移出我的站", nav: "步行導航",
    stale2: "這站的資料是 {m} 分鐘前的", excluded: "旗津的站，卡車路線不會排到", inCampus: "校內", nearCampus: "校外鄰近",
    favAdded: "加進我的站了", favRemoved: "移出我的站了", close: "關閉",

    kpi: "校園這一帶", kpiSub: "校園到捷運之間 {n} 站", uSta: "站", uRide: "人次", kEmpty: "現在沒車", kRisk: "30 分內可能被借光", kUnmet: "未來 {h} 分預估借不到車", kSaved: "這一趟可以少掉",
    plan: "校園專車的下一趟", copy: "複製路線", copied: "已複製",
    pickN: "載走 {n} 台", dropN: "補 {n} 台", nowAt: "現在 {b}/{c}", eta: "分後到", onTruck: "車上 {n} 台", truck: "卡車 {k}", nStops: "{n} 站",
    tripLen: "約 {t} 分鐘、{k} 公里", tripGain: "預估少 {v} 人次借不到車",
    noPlan: "現在不用出車。校園這一帶借不到車的人次很少，最多的一站也只有 {m} 人次。", offWindow: "路線只在 06:00 到 23:00 之間規劃。",
    riskH: "最可能沒車的站", unmetH: "未來 90 分缺最多車的站", h30: "30 分", h60: "60 分", hU: "90 分缺口",

    legBike: "你走到的時候", legDock: "你騎到的時候", legP: "{h} 分內沒車的機率", legU: "未來 {h} 分借不到車的人次",
    legNumBike: "數字是現在可借的車", legNumDock: "數字是現在的空位", legCampus: "藍框是校內的站", legRoute: "卡車路線",
    keyH: "地圖和清單怎麼看", 
    trackH: "建議的紀錄", trackSub: "從 {d} 起，頁面每 10 分鐘先把建議寫下來，之後再對紀錄器上的實際車數。目前有 {n} 個上課日。",
    trackLeave: "傍晚從校內借車", trackArrive: "早上在山下借車", trackDock: "早上到校內還車",
    trackLine: "{n} 次。照建議平均 {a} 分鐘騎上車，看官方 App 的車數是 {b} 分鐘，走到最近的站是 {c} 分鐘。",
    trackLineDock: "{n} 次。照建議平均多花 {a} 分鐘，看官方 App 的空位是 {b} 分鐘，騎到最近的站是 {c} 分鐘。",
    trackSee: "出發前 20 分鐘預告的時間，平均差 {x} 分鐘。", trackNone: "紀錄剛開始，次數還不夠。",
    keyYes: "綠色是你到的時候應該有車。還車那一頁是應該有位子。圓圈裡的數字是現在的數量。", keyMaybe: "黃色是不一定，十次裡大概有一到四次會撲空。", keyNo: "紅色是很可能沒有。",
    keyGone: "深紅是現在就沒有，短時間內也不太會有。", keyNone: "灰色是暫停服務或沒有資料。",
    keyRing: "地圖上圓圈外緣的弧線是車柱有車的比例，藍框是校內的站。", keyRoute: "虛線是建議的卡車路線，圓圈裡的數字是停靠順序。",
    aboutWhat: "<h3>這個頁面在做什麼</h3><p>上課日傍晚 5 點半到 6 點多，在中山校內找一台 YouBike 平均要 5 分鐘，八次有一次超過 10 分鐘。其他時段大約 2 分鐘。早上 9 點到 11 點則是校內的車柱常停滿。這個頁面告訴你現在出發幾分鐘後騎得上車、晚一點出發會不會更久，還有騎車和走路哪個快。</p>",
    aboutProof: "<h3>我們對過的答案</h3><p>拿 12 個沒有用來估模型的上課日重播：每 10 分鐘在每一站放一個人，看他幾分鐘後騎上車，第一站撲空就走到下一站。</p>" +
      "<p>挑站這件事，頁面幫不了太多。直接走到最近的站，或是先看車數再走到最近有車的站，傍晚平均都是 3.7 分鐘。這個頁面的第一版只推薦九成以上有車的站，結果是 5.3 分鐘，多走的路比撲空的代價大。現在改成推薦預期最快的站，同樣是 3.7 分鐘。</p>" +
      "<p>頁面多出來的是事先知道。出發前 10 到 30 分鐘，它判斷這一趟會不會超過 8 分鐘的準度（AUC）是 0.86 到 0.90，只看當下的車數是 0.69 到 0.78。傍晚從校內到捷運站，借車騎過去平均 11.6 分鐘，走路 17.3 分鐘。</p>",
    aboutHow: "<h3>數字怎麼來的</h3>" +
      "<p>車數和空位來自 YouBike 官方 API。紀錄器每 10 分鐘抓一次中山大學周邊 5 公里內的 {n} 個站，從 2026 年 10 月 1 日記到現在。校園到捷運之間的 19 站，頁面開著的時候每分鐘會直接向官方讀一次最新的數字。</p>" +
      "<p>「你到的時候有沒有車」把每一站當成一條生滅鏈：借走一台少一台，還進一台多一台。借還的速率用紀錄器的資料估，校園到捷運之間的 19 站在上課日每 10 分鐘估一組，因為下課那 10 分鐘借得特別快。從現在的車數往後推到你走到的那一刻，九成以上寫「應該有車」，六成到九成寫「不一定」。還車的門檻是九成五和七成。</p>" +
      "<p>建議的站是預期最快的一站：走過去的時間，加上撲空的機會乘上再走到下一站的時間。和它差不到半分鐘的站裡，挑最有把握的那一站。步行和騎車的時間用 OpenStreetMap 的路網距離算，步行每分鐘 80 公尺，騎車每分鐘 200 公尺，沒有算坡度。校內有些小路地圖上沒有，路網距離超過直線 1.7 倍時以 1.7 倍計。</p>" +
      "<p>調度那一頁只排一台顧校園這一帶的卡車。先估每一站未來 {h} 分有幾個人借不到車，再搜尋路線，決定去哪一站載、送到哪一站。一台卡車最多載 {q} 台、時速 {s} 公里、每站停 {st} 分鐘。用估出來的借還速率模擬，這樣一台車讓傍晚校內借不到車的人次少 34%，讓早上山下借不到車的人次少 70%。在臺大用真實的騎乘紀錄重播，1、3、6 台卡車少 13%、30%、45%。</p>" +
      "<p>調度頁的「30 分內可能被借光」用的是另一個模型：LightGBM，先用臺大周邊 10 個月的資料訓練，再用中山的資料微調。</p>" +
      "<p>「我的站」和你選的起點只存在這台裝置的瀏覽器裡，不會上傳。</p>",
    langK: "語言", credit: "人工智慧導論期末專案，第 54 組。程式和資料放在 <a href=\"https://github.com/alexlin8888/nsysu-youbike-log\" target=\"_blank\" rel=\"noopener\">GitHub</a>。",
    gripLabel: "拉高或收合清單", playLabel: "播放", pauseLabel: "暫停", sliderLabel: "時間", dayLabel: "日期", modeLabel: "即時或重播", horizonLabel: "排序依據", mapLabel: "站點地圖",
    weekdays: ["日", "一", "二", "三", "四", "五", "六"]
  },
  en: {
    docTitle: "Beat the Bell | NSYSU YouBike", where: "NSYSU YouBike",
    live: "Live", replay: "Replay", tabRider: "Borrow", tabDock: "Return", tabOps: "Dispatch", tabAbout: "About",
    loading: "Loading data", liveAt: "Updated {t}", ago: "{m} min ago", agoH: "{h} h ago", justNow: "just now", replayAt: "Replay {d} {t}",
    stale: "Can't reach new data. Showing the {t} snapshot.",
    stalebig: "The logger has sent nothing for {m} min. This is its last snapshot.",
    loadFail: "The data did not load ({e}). Reload the page, or try again in a few minutes.",
    replayFail: "This day's replay did not load ({e}).",

    bellNext: "Next class ends", bellIn: "in {m} min", bellInH: "in {h} h {m} min", inMin: "{m} min", inHour: "{h} h {m} min", nowIs: "now {t}",
    offdayBig: "No classes today", offdayNote: "No end-of-class rush on a day off", overBig: "Classes are over", overNote: "The last one ended at {t}",
    stBikeOk: "Bikes are easy to find on campus", stBikeLow: "Campus is running low on bikes", stBikeOut: "Campus is nearly out of bikes",
    stDockOk: "Docks are easy to find on campus", stDockLow: "Campus docks are filling up", stDockOut: "Campus docks are nearly full",

    search: "Search stations, e.g. Library", noMatch: "No station by that name",
    originK: "From", destK: "To", goalK: "To", toNone: "Anywhere", grpCampus: "Campus", grpTown: "Town", grpOther: "Other", oMe: "My location", oPick: "Pick on the map",
    whenBikeK: "Leaving", whenDockK: "Arriving", wNow: "Now", wBell: "After {t} class", wPlus: "In {m} min",
    geoFail: "Couldn't get your location. Pick a point on the map instead.", tooFar: "You are far from NSYSU, so the place stays on campus.", picking: "Tap the map to set where you start", pickingDest: "Tap the map to set where you are going", fabLabel: "Use my location",
    bestBikeNow: "Borrow here now", bestBikeBell: "Borrow here after the {t} class", bestDock: "Return here",
    skipBike: "{n} is closer but will probably be out when you get there", skipDock: "{n} is closer but will probably be full when you get there",
    weakBike: "No station nearby is sure to have a bike.", weakDock: "No station nearby is sure to have a free dock.",
    noneBike: "No station within 2 km is reporting", noneDock: "No station near the destination is reporting",
    expect: "about {b} left by then", docksNow: "{d} free docks now", docksNow1: "1 free dock now", bikesNow: "{b} bikes now",
    tipSoon: "Leave before {t} and you ride within about {a} min. Leaving at {u} takes about {b}.", tipCalm: "Leave any time in the next hour and you ride within about {a} min.", 
    relayTag: "+NT$5", relayRetHere: "This station is likely still empty when you arrive (about {o} in 10). Returning here earns a NT$5 ride voucher.", relayRetAlt: "{n} is likely still empty when you arrive (about {o} in 10). Returning there earns a NT$5 ride voucher, for about {m} min more.",
    relayBorHere: "This station is likely still full when you arrive (about {o} in 10). Borrowing here earns a NT$5 ride voucher.", relayBorAlt: "{n} is likely still full when you arrive (about {o} in 10). Borrowing there earns a NT$5 ride voucher, for about {m} min more on foot.",
    relayCardRet: "Likely still empty when you arrive (about {o} in 10). Returning an ordinary bike here earns a NT$5 ride voucher.", relayCardBor: "Likely still full when you arrive (about {o} in 10). Borrowing here earns a NT$5 ride voucher.",
    aboutRelay: "<h3>What +NT$5 means</h3><p>Since July 2026 YouBike in Kaohsiung runs a friendship relay: borrowing at a full station, or returning an ordinary bike to an empty one, earns a NT$5 ride voucher, every day from 06:00 to 24:00. The state of the station at the moment you borrow or return decides. The operator’s app shows which stations are empty or full now, and this page marks the ones likely to be so when you get there. On 12 teaching days, 71% of the stations it marked were still empty 10 minutes later, against 65% of the stations that were simply empty at the time. Whether a voucher is issued is the operator’s call.</p>",
    odds: "about {n} in 10", tipOn: "If it is empty, {n} is {m} min further on foot.", tipOnDock: "If it is full, {n} is {m} min further by bike.", tipSure: "For a surer bet, {n} is a {m} min walk.", tipSureDock: "For a surer bet, return at {n}, {m} min from where you are going.",
    walkWins: "Walking is faster", walkAll: "{m} min on foot", walkVs: "By bike about {m} min, with the walk to a bike and the return", tripRide: "Borrow, ride and return: about {a} min door to door. On foot: {b} min.",
    laterH: "Minutes until you ride, by when you leave", laterSub: "forecast", nearFresh: "counts as of {t}",
    fav: "My stations", near: "Nearby", nearBike: "colour: when you get there on foot", nearDock: "colour: when you ride in", more: "Show 8 more", less: "Show fewer",
    walkK: "walk", walkDest: "to destination", walkMin: "{m} min", farK: "away", walkKm: "{k} km",
    cBikeYes: "Should have a bike", cBikeMaybe: "May be out", cBikeNo: "Probably out", sGone: "No bikes now",
    cDockYes: "Should have a dock", cDockMaybe: "May be full", cDockNo: "Probably full", sFullNow: "Full now", sNone: "No data", sOos: "Out of service",
    tGone: "likely out by {t}", tKeep: "bikes until {t}", tBack: "a bike likely back by {t}", tNoBack: "probably none before {t}",
    tFull: "likely full by {t}", tFree: "docks until {t}", tOpen: "a dock likely free by {t}", tNoOpen: "probably full until {t}",
    usualBikeCampus: "When campus usually runs out", usualDockCampus: "When campus is usually full", usualBikeGate: "When this area usually runs out", usualDockGate: "When this area is usually full",
    usualTeach: "teaching-day average", usualOff: "day-off average", usualPeak: "hardest {a} to {b}", usualEasy: "easy all day",

    fBikes: "Bikes", fDocks: "Free docks", fArrive: "When you arrive", aheadH: "Next 90 minutes", aheadBike: "expected bikes", aheadDock: "expected free docks",
    chartCap: "Bikes today. Vertical dashes are class ends; the dashed line is the forecast.", addFav: "Save station", rmFav: "Remove station", nav: "Walking directions",
    stale2: "This station last reported {m} min ago", excluded: "A Qijin station; the truck route never includes it", inCampus: "on campus", nearCampus: "near campus",
    favAdded: "Saved to My stations", favRemoved: "Removed from My stations", close: "Close",

    kpi: "Around campus", kpiSub: "{n} stations between campus and the metro", uSta: "stations", uRide: "riders", kEmpty: "empty now", kRisk: "likely to run out within 30 min", kUnmet: "expected to find no bike in the next {h} min", kSaved: "spared by this trip",
    plan: "Next trip of the campus truck", copy: "Copy route", copied: "Copied",
    pickN: "Pick up {n}", dropN: "Drop off {n}", nowAt: "now {b}/{c}", eta: "min away", onTruck: "{n} on the truck", truck: "Truck {k}", nStops: "{n} stops",
    tripLen: "about {t} min, {k} km", tripGain: "about {v} fewer riders left without a bike",
    noPlan: "No trip is needed now. Few riders around campus are expected to find no bike, {m} at the worst station.", offWindow: "Routes are planned between 06:00 and 23:00 only.",
    riskH: "Most likely to run out", unmetH: "Largest shortfall, next 90 min", h30: "30 min", h60: "60 min", hU: "Shortfall",

    legBike: "When you get there on foot", legDock: "When you ride in", legP: "Chance of no bikes within {h} min", legU: "Riders without a bike, next {h} min",
    legNumBike: "The number is bikes available now", legNumDock: "The number is free docks now", legCampus: "A blue outline marks a campus station", legRoute: "Truck route",
    keyH: "Reading the map and the list", 
    trackH: "The record", trackSub: "Since {d} the page writes down its advice every 10 minutes and checks it against the counts logged afterwards. {n} teaching days so far.",
    trackLeave: "Leaving campus in the evening", trackArrive: "Borrowing at the foot of the campus in the morning", trackDock: "Returning on campus in the morning",
    trackLine: "{n} cases. With the page: {a} min until riding on average. With the operator's counts: {b}. Walking to the nearest station: {c}.",
    trackLineDock: "{n} cases. With the page: {a} min extra on average. With the operator's counts: {b}. Riding to the nearest station: {c}.",
    trackSee: " What the page said 20 minutes ahead was off by {x} min on average.", trackNone: "The record has just started.",
    keyYes: "Green: there should be a bike when you get there. On the Return tab, a free dock. The number in the circle is the count right now.", keyMaybe: "Yellow: not certain. You would come up empty one to four times in ten.", keyNo: "Red: probably none.",
    keyGone: "Dark red: none right now, and little chance of one soon.", keyNone: "Grey: out of service or no data.",
    keyRing: "On the map, the arc around a circle is the share of docks holding a bike. A blue outline marks a campus station.", keyRoute: "The dotted line is the suggested truck route; the numbers are the order of its stops.",
    aboutWhat: "<h3>What this page does</h3><p>On teaching days between 17:30 and a little after 18:00, finding a YouBike on the NSYSU campus takes 5 minutes on average, and more than 10 minutes one time in eight. At other times it takes about 2. From 09:00 to 11:00 the campus docks are often full. This page tells you how many minutes it will take to be on a bike if you leave now, whether leaving later will take longer, and whether riding beats walking.</p>",
    aboutProof: "<h3>What we checked</h3><p>We replayed 12 teaching days that were not used to fit the model. Every 10 minutes a rider stands near each station; we count the minutes until that rider is on a bike, walking on to the next station when the first one is empty.</p>" +
      "<p>For choosing a station the page adds little. A rider who walks to the nearest station, or to the nearest one that shows a bike, needs 3.7 minutes in the evening. The first version of this page only named stations with a 90% chance, and that took 5.3 minutes: the extra walking cost more than the misses it avoided. The page now names the station with the fewest expected minutes, which also takes 3.7.</p>" +
      "<p>What the page adds is notice. Asked 10 to 30 minutes before a rider leaves whether the search will take more than 8 minutes, it separates the two cases with an AUC of 0.86 to 0.90; the current counts alone give 0.69 to 0.78. From campus to the metro in the evening, the bike takes 11.6 minutes door to door on average and walking takes 17.3.</p>",
    aboutHow: "<h3>Where the numbers come from</h3>" +
      "<p>Bike and dock counts come from the official YouBike API. A logger reads the {n} stations within 5 km of NSYSU every 10 minutes and has done so since 1 October 2026. For the 19 stations between campus and the metro, the page itself reads the operator's counts once a minute while it is open.</p>" +
      "<p>Whether a station will have a bike when you arrive comes from a birth-death chain: a rental removes a bike, a return adds one. The rental and return rates are fitted to the logger's data, with one pair per 10 minutes of a teaching day for the 19 stations between campus and the metro, because the 10 minutes after a bell are much busier. The chain runs from the count now to the minute you arrive. A chance of 90% or more reads \"should have a bike\", 60% to 90% reads \"may be out\". For docks the two thresholds are 95% and 70%.</p>" +
      "<p>The suggested station is the one with the fewest expected minutes: the walk there, plus the chance of a miss times the walk on to the next station. Among the stations within half a minute of that, the page names the surest. Walking and riding times use path lengths from OpenStreetMap at 80 m and 200 m per minute; slopes are not counted. Some campus footpaths are missing from the map, so a path is never taken to be longer than 1.7 straight lines.</p>" +
      "<p>The Dispatch tab plans one truck for the campus area. It estimates how many riders will find no bike at each station over the next {h} minutes, then searches for a route: where to load and where to deliver. A truck holds {q} bikes, drives at {s} km/h and spends {st} minutes per stop. In a simulation driven by the fitted rates, one such truck avoids 34% of the evening's failed rentals on campus and 70% of the morning's at the foot of the campus. Replayed on real trips at NTU, 1, 3 and 6 trucks avoid 13%, 30% and 45%.</p>" +
      "<p>\"Likely to run out within 30 min\" on the Dispatch tab comes from a second model: LightGBM, trained on 10 months of data around NTU and fine-tuned on the NSYSU logger.</p>" +
      "<p>\"My stations\" and the places you choose are stored only in this browser.</p>",
    langK: "Language", credit: "Final project for Introduction to Artificial Intelligence, Group 54. Code and data are on <a href=\"https://github.com/alexlin8888/nsysu-youbike-log\" target=\"_blank\" rel=\"noopener\">GitHub</a>.",
    gripLabel: "Expand or collapse the list", playLabel: "Play", pauseLabel: "Pause", sliderLabel: "Time", dayLabel: "Day", modeLabel: "Live or replay", horizonLabel: "Rank by", mapLabel: "Station map",
    weekdays: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
  }
};
