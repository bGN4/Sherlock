/*
**************************

[rewrite_local]
https://m\.weibo\.cn/api/attentionvist/groupsMembersByTag url script-response-body https://github.com/bGN4/Sherlock/raw/master/weibo.mitm.follows.js

[mitm]
hostname = *.weibo.cn, *.weibo.com

**************************/

const dogs = {
  "1263406744":{"mark":0.5,"name":"🐴"},
  "1481944214":{"mark":1.0,"name":"🐘"},
  "1633537680":{"mark":1.0,"name":"🌍"},
  "1647486362":{"mark":1.0,"name":"🦅"},
  "2150758415":{"mark":1.0,"name":"🪰"},
  "2281157913":{"mark":1.0,"name":"🌊"},
  "3812400789":{"mark":1.0,"name":"🈚️"},
  "3939426052":{"mark":1.0,"name":"🐻"},
  "5067914848":{"mark":1.0,"name":"🦐"},
  "5721376081":{"mark":1.0,"name":"🇹🇼"},
  "5944260564":{"mark":1.0,"name":"🪰"},
  "6059492811":{"mark":1.0,"name":"拆"},
  "6631101126":{"mark":1.0,"name":"拆"},
  "6865526227":{"mark":1.0,"name":"🈚️"},
  "7010131150":{"mark":1.0,"name":"8⃣️"},
  "7522215527":{"mark":1.0,"name":"🌍"},
  "7628706247":{"mark":1.0,"name":"🍌"},
  "7690478167":{"mark":1.0,"name":"🍌"}
};
const $ = initial();
var body = "";
if( typeof($response) !== "undefined" ) {
  body = $response.body || "";
}
const size = body.length;
const url = $request.url;
const cookie = $request.headers['Cookie'] || "";

if( size<10 ) {
  console.log("● testing ●");
  $.done();
} else if (size > 987654) {
  $.notify("● oversize ●", "", ""+size, null);
  $.done();
} else {
  console.log("● rewrite ●");
//console.log(Object.entries($request.headers));
  var obj = JSON.parse(body);
  if( Array.isArray((obj.data||{}).member_users) &&
    obj.data.member_users.length>0 ) {
    let count = obj.data.member_users.length;
    let total = obj.data.member_count;
    let stats = {0.5: 0, 1.0: 0};
    let names = {0.5:[], 1.0:[]};
    let follower = count + "/" + total + "个";
    obj.data.member_users.forEach((user) => {
      let name = (dogs[user.idstr]||{}).name;
      let mark = (dogs[user.idstr]||{}).mark;
      if( user.idstr in dogs &&
        !names[0.5].includes(name) &&
        !names[1.0].includes(name) ) {
        if( mark<1.0 ) names[0.5].push(name);
        else names[1.0].unshift(name);
        stats[mark] += 1;
      }
    });
    console.log("● hooking ●");
    obj.data.member_users.splice(0, 0, {
      "screen_name": "___________",
      "followers_count_str": "1个",
      "verified_reason": "认证",
      "descStruct": {
        "labelDesc": [{
          "suffix": "粉丝",
          "name": "4321",
          "followers_count_str": follower
        }, {
          "name": "" + stats[1.0] * 1.0,
          "highlight": 1
        }, {
          "name": "" + stats[0.5] * 0.5
        }],
        "textDesc": names[1.0].join('/')
      },
      "status": {
        "text": names[0.5].join('/')
      }
    });
  } else {
    console.log(body);
  }
  $.done({body: JSON.stringify(obj)});
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