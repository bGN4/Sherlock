/*
**************************

[rewrite_local]
https://m?api\.weibo\.(cn|com)/2/comments/build_comments url script-response-body https://github.com/bGN4/Sherlock/raw/master/weibo.mitm.comment.js

[mitm]
hostname = *.weibo.cn, *.weibo.com

**************************/

const province = ["安徽","北京","重庆","福建","甘肃","广东","广西","贵州","海南","河北","黑龙江","河南","湖北","湖南","江苏","江西","吉林","辽宁","内蒙古","宁夏","青海","山东","上海","山西","陕西","四川","天津","新疆","西藏","云南","浙江","海外","香港","澳门","台湾"];
const $ = initial();
const key = "weibo.csv";
const ids = do_load();
var body = "";
if( typeof($response) !== "undefined" ) {
  body = $response.body || "";
}
const size = body.length;

if( size < 10 ) {
  console.log("● fetching ●");
  $.get({
    url: 'https://github.com/bGN4/Sherlock/raw/master/weibo.csv',
    headers: {}
  }, function(err, resp, data) {
    if( err ) {
      console.log("● error: " + err);
    } else {
      console.log("● updating ●");
      ids.length = 0;
      let lines = data.split("\n");
      for( let i=1; i<lines.length; i++ ) {
        ids.push(lines[i].split(",")[0]);
      }
      $.write(JSON.stringify(ids), key);
      let uids = do_load();
      let test = uids.includes("0000000000");
      console.log("● " + test + " ●");
    }
    $.done();
  });
} else if (size > 987654) {
  $.notify("● oversize ●", "", ""+size, null);
  $.done();
} else {
  console.log("● rewrite ●");
//console.log(Object.entries($request.headers));
//txt = body.replace(/"\w+_20\d\d":0,/g, "");
  txt = body.replace(/"badge":{[\w\d:",]+},/g, "");
  console.log("● ↓" + size + "↓");
  console.log("● ↑" + txt.length + "↑");
//console.log("☀☀☀☀☀");
//console.log(txt);
  if(size > 432100) {
    $.notify("● oversize ●", ""+size,
             ""+txt.length, null);
  }
  var obj = JSON.parse(txt);
  console.log("● hooking ●");
  fOne(obj.rootComment);
  fList(obj.datas);
  fList(obj.comments); // subcomments
  fList(obj.root_comments);
  $.done({body: JSON.stringify(obj)});
}

function do_load() {
  console.log("● reading ●");
  var ids = JSON.parse($.read(key) || "[]");
  console.log("● " + ids.length + " ●");
  return ids;
}

function web_load() {
  return new Promise(resolve => {
    var req = {
      url: '',
      headers: {}
    };
    $.get(req, function(err, resp, data) {
      resolve(data);
    });
  });
}

function fixLoc(locate) {
  var loc = "" + locate;
  if( loc.startsWith("中国") &&
      loc.length > 2 ) loc = loc.slice(2);
  if( loc.indexOf(" ") < 0 ) return loc;
  var lol = loc.split(" ");
  if( province.includes(lol[0]) ) {
    loc = lol[1];
  }
  return loc.trim();
}

function getLoc(source) {
  var loc = "＿＿";
  if( typeof(source) === "string" ) {
    let pos = source.indexOf("来自") + 2;
    if( pos > 1 ) {
      loc = source.slice(pos, -4);
    }
  }
  if( loc.startsWith("中国") &&
      loc.length > 2 ) loc = loc.slice(2);
  return loc.trim();
}

function getExt(user) {
  var reg_at = "" + user.created_at;
  return "(" + reg_at.slice(-2) + ", " +
             user.friends_count + ", " +
             user.statuses_count + ")";
}

function fOne(item) {
  if( typeof(item) !== "object" ) return 0;
  if( !("user" in item) ) return 0;
  item.text += "\n" +
          "【" + fixLoc(item.user.location) +
          "→" + getLoc(item.source) + "】";
  item.text += "\t" + getExt(item.user);
  if( ids.includes(item.user.idstr) ) {
    item.user.name = "☒" + item.user.name;
    item.user.screen_name = "❌" +
              item.user.screen_name;
    return item.user.id;
  } else if("reply_comment" in item &&
      "reply_original_text" in item) {
    let reply = item.reply_comment;
    if( ids.includes(reply.user.idstr) ) {
      item.user.screen_name = "⭕️" +
                item.user.screen_name;
      return reply.user.id;
    }
  }
  return 0;
}

function fList(list) {
  if( !(Array.isArray(list)) ) return;
//for( let i=0; i<list.length; i++ ) {
  list.forEach((item) => {
    let x = -1;
    if ( "user" in item ) {
      x = fOne( item );
    } else if ( item.type == 0 &&
      typeof(item.data) === "object") {
      x = fOne( item.data );
    } else {
      console.log("● warning ●");
      Object.keys(item).forEach((k) => {
        let type = typeof item[k];
        if ( type === 'string' ||
             type === 'number' ) {
          console.log("● "+k+":"+item[k]);
        } else {
          console.log("● "+k+":"+type);
        }
      });
    }
  });
}

function initial() { // Modified from https://github.com/NobyDa/Script/
  const start = Date.now();
  const isRequest = typeof $request != "undefined";
  const isSurge = typeof $httpClient != "undefined";
  const isQuanX = typeof $task != "undefined";
  const isLoon = typeof $loon != "undefined";
  const notify = (title, subtitle, message, rawopts) => {
    const Opts = (rawopts) => { // Modified from https://github.com/chavyleung/scripts/blob/master/Env.js
      if (!rawopts) return rawopts
      if (typeof rawopts === 'string') {
        if (isLoon) return rawopts
        else if (isQuanX) return {
          'open-url': rawopts
        }
        else if (isSurge) return {
          url: rawopts
        }
        else return undefined
      } else if (typeof rawopts === 'object') {
        if (isLoon) {
          let openUrl = rawopts.openUrl || rawopts.url || rawopts['open-url']
          let mediaUrl = rawopts.mediaUrl || rawopts['media-url']
          return {
            openUrl,
            mediaUrl
          }
        } else if (isQuanX) {
          let openUrl = rawopts['open-url'] || rawopts.url || rawopts.openUrl
          let mediaUrl = rawopts['media-url'] || rawopts.mediaUrl
          return {
            'open-url': openUrl,
            'media-url': mediaUrl
          }
        } else if (isSurge) {
          let openUrl = rawopts.url || rawopts.openUrl || rawopts['open-url']
          return {
            url: openUrl
          }
        }
      } else {
        return undefined
      }
    }
    console.log(`${title}\n${subtitle}\n${message}`)
    if (isQuanX) $notify(title, subtitle, message, Opts(rawopts))
    if (isSurge) $notification.post(title, subtitle, message, Opts(rawopts))
  }
  const adapterStatus = (response) => {
    if ( response ) {
      if ( response.status ) {
        response["statusCode"] = response.status;
      } else if ( response.statusCode ) {
        response["status"] = response.statusCode;
      }
    }
    return response;
  }
  const get = (options, callback) => {
    if( isQuanX ) {
      if(typeof options == "string") options = {
        url: options
      };
      options["method"] = "GET";
      $task.fetch(options).then(response => {
        callback(null, adapterStatus(response), response.body);
      }, reason => callback(reason.error, null, null));
    }
    if( isSurge ) {
      options.headers['X-Surge-Skip-Scripting'] = false;
      $httpClient.get(options, (error, response, body) => {
        callback(error, adapterStatus(response), body);
      });
    }
  }
  const write = (value, key) => {
    if( isQuanX ) return $prefs.setValueForKey(value, key);
    if( isSurge ) return $persistentStore.write(value, key);
  }
  const read = (key) => {
    if( isQuanX ) return $prefs.valueForKey(key);
    if( isSurge ) return $persistentStore.read(key);
  }
  const done = (value = {}) => {
    let spend = ((Date.now() - start) / 1000).toFixed(2);
    console.log("▲ " + spend + "s ▲");
    console.log("▲ ▲ ▲ ▲ ▲ ▲");
    if (isQuanX) return $done(value);
    if (isSurge) isRequest ? $done(value) : $done();
  }
  console.log("▼ ▼ ▼ ▼ ▼ ▼");
  return {
    isRequest,
    isSurge,
    isQuanX,
    isLoon,
    notify,
    write,
    read,
    done,
    get
  };
}