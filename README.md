# Sherlock→ShareBlock→共享黑名单→云拉黑

[![Demo](https://img.shields.io/badge/link-demo-brightgreen.svg?style=plastic)](https://blocking.azurewebsites.net/)

## 适用场景

* 将旧ID的黑名单导出，并导入到新ID
* 在多ID或多人之间同步黑名单
* 部署WEB服务后通过API实现更多操作

## 使用方法

### [weibo.py](weibo.py)

```console
# 导入黑名单
python weibo.py import -C config.json
# 导出黑名单
python weibo.py export -C config.json
# 更新黑名单
python weibo.py export -C config.json -N 1
# 命令行参数详解
python weibo.py -h
```

### [zhihu.py](zhihu.py)

```console
# 帮助
python zhihu.py -h
```

## 数据格式

### [config.json](config.json)

```json
{}
```

### [weibo.csv](weibo.csv)

uid | alia | name | src | note | time
:-: | :-: | :-: | :-: | :-: | :-:
用户ID | 个性域名 | 微博昵称 | 拉黑来源 | 原因备注 | 拉黑时间

### [zhihu.csv](zhihu.csv)

## 研发笔记
### [拉黑心得](notes.md)
