# Sherlock→ShareBlock→共享黑名单→云拉黑

[![Demo](https://img.shields.io/badge/link-demo-brightgreen.svg?style=plastic)](https://blocking.azurewebsites.net/)

## 适用场景

* 将旧ID的黑名单导出，并导入到新ID
* 在多ID或多人之间同步黑名单
* 部署WEB服务后通过API实现更多操作
  - 在评论区等场景标记或隐藏黑名单用户

## 使用准备

1. 安装 [Python](https://www.python.org/downloads/) 环境
2. 安装依赖库：pip install -r [requirements.txt](requirements.txt)
3. 浏览器中打开 weibo.cn ，F12启动开发者工具后登录
4. 提取 User-Agent 并填入 [config.json](config.json#L9) 中对应位置
5. 提取 Cookie 并填入 [config.json](config.json#L10) 中对应位置
6. 准备完成（数日后Cookie过期需重新登录并提取）

## 使用方法

### [weibo.py](weibo.py)

```console
# 导出黑名单
python weibo.py export -C config.json
# 导入黑名单
python weibo.py import -C config.json -I weibo.csv
# 更新黑名单（N页，每页10个）
python weibo.py export -C config.json -N 1
# 移出黑名单
python weibo.py remove -C config.json -U UID1 UID2 ...
# 命令行参数详解
python weibo.py -h
```

## 数据格式

### [config.json](config.json)

```json
{
    "其他配置": "无需更改",
    "headers": {
        "User-Agent": "浏览器UA",
        "Cookie": "你的Cookie"
    }
}
```

### [weibo.csv](weibo.csv)

uid | alias | name | okamoto | src | note | time
:-: | :-: | :-: | :-: | :-: | :-: | :-:
用户ID | 个性域名 | 微博昵称 | 冈本密接 | 拉黑来源 | 原因备注 | 拉黑时间

## 研发笔记
### [拉黑心得](notes.md)
