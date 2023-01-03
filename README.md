# picobbs

Pico 论坛每日积分任务脚本，积分规则：
- 每日签到获得 1-200 积分
- 每日发帖获得 100 积分
- 每日评论，获得 5 积分，最多评论 20 次

# 使用方式

1. 登录 [Pico 社区](https://bbs.picoxr.com/)
2. 找到名为 `sessionid` 的 cookie，填入到脚本中

```python
if __name__ == "__main__":
    cli = PicoBBS(session_id="<cookie 中的 sessionid 值>", channels=[
        Echo(),
        LarkChannel("<飞书 webhook>"),
        WorkWechatBotChannel("<企业微信机器人 key>"),
    ])
    cli.sign()          # 执行每日签到
    cli.publish_post()  # 每日发帖
    cli.comment()       # 发送 20 个评论
```

3. 安装依赖：`pip install -r requirements.txt`
4. 运行脚本：`python pico.py`
5. [可选] 设置 cronjob 每日运行
6. 运行效果
![image](https://user-images.githubusercontent.com/14919255/210379037-bfd44dba-b736-43ed-9a51-1b95e57cdfcd.png)