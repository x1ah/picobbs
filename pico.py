import os
import logging
import random
import time
from typing import List, Tuple

import requests


logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(asctime)s: %(message)s"
)


class MsgChannel:
    name: str = "unknown channel"

    def send(self, text: str):
        raise NotImplemented("not implemented")


class LarkChannel(MsgChannel):
    name = "飞书自定义机器人"

    def __init__(self, webhook: str) -> None:
        self.webhook = webhook

    def send(self, text: str):
        return requests.post(
            self.webhook, json={"msg_type": "text", "content": {"text": text}}
        )


class PicoBBS:
    session_id: str
    logger: logging.Logger
    channel: MsgChannel

    def __init__(self, session_id: str, channels: List[MsgChannel] = None) -> None:
        self.session_id = session_id
        self.logger = logging.getLogger(__name__)
        self.channels = channels or []

    @property
    def session(self) -> requests.Session:
        if not getattr(self, "_session", None):
            self._session = requests.Session()

        return self._session

    @property
    def cookies(self):
        return {"sessionid": self.session_id}

    @property
    def http_headers(self):
        return {
            "authority": "bbs.picoxr.com",
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "origin": "https://bbs.picoxr.com",
            "referer": "https://bbs.picoxr.com",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        }

    def notify(self, text: str):
        for channel in self.channels:
            try:
                channel.send(text)
            except Exception as e:
                self.logger.error(f"send msg error: {str(e)}")

    def sign(self):
        url = "https://bbs.picoxr.com/ttarch/api/growth/v1/checkin/create?app_id=264482&service_id=0&lang=zh-Hans-CN&web_id=7184406560655279619"
        resp = self.session.post(url=url, cookies=self.cookies)
        if resp.status_code != 200:
            self.logger.error(f"sign error: {resp.text}")
            return

        try:
            point = resp.json().get("data", {}).get("point_records", [])[0]["score"]
        except Exception as e:
            self.logger.error(f"parse point error: {str(e)}")
            return

        self.notify(f"论坛每日签到成功，获得 {point} 积分")

    def get_post_content(self) -> Tuple[str, str, str]:
        """默认发一首古诗"""
        default_title = "每日一首古诗：关山月（李白•唐代）"
        default_abstract = "明月出天山，苍茫云海间。\n长风几万里，吹度玉门关。\n汉下白登道，胡窥青海湾。\n由来征战地，不见有人还。\n戍客望边邑，思归多苦颜。\n高楼当此夜，叹息未应闲。"
        default_content = "<p>明月出天山，苍茫云海间。<br />长风几万里，吹度玉门关。<br />汉下白登道，胡窥青海湾。<br />由来征战地，不见有人还。<br />戍客望边邑，思归多苦颜。<br />高楼当此夜，叹息未应闲。</p>"
        content = self.session.get("https://v2.jinrishici.com/one.json")
        if content.status_code != 200:
            self.logger.error(f"generate post content error: {content.text}")
            return default_title, default_abstract, default_content

        content_json = content.json()["data"]
        title = content_json.get("origin", {}).get("title", "")
        author = content_json.get("origin", {}).get("author", "")
        dynasty = content_json.get("origin", {}).get("dynasty", "")
        abstract = "\n".join(content_json.get("origin", {}).get("content", []))
        text = "<br />".join(content_json.get("origin", {}).get("content", []))
        if not all([title, author, dynasty, text, abstract]):
            self.logger.warning(f"get shici content error: {content_json}")
            return default_title, default_abstract, default_content

        return f"每日一首古诗打卡：{title}（{author}•{dynasty}）", abstract, f"<p>{text}</p>"

    def publish_post(self):
        title, abstract, text = self.get_post_content()
        draft = self.session.post(
            "https://bbs.picoxr.com/ttarch/api/content/v1/content/create?app_id=264482&service_id=0&lang=zh-Hans-CN&web_id=7184406560655279619", 
            headers=self.http_headers,
            cookies=self.cookies,
            json={
                "content": {
                    "item_type": 2,
                    "content": text,
                    "abstract": abstract,
                    "name": title,
                    "mime_type": "html",
                }
            }
        )
        if draft.status_code != 200:
            self.logger.error(f"create post draft error: {draft.text}")
            return

        item_id = draft.json()["data"]["item_id"]
        publish_resp = self.session.post(
            "https://bbs.picoxr.com/ttarch/api/content/v1/content/publish?app_id=264482&service_id=0&lang=zh-Hans-CN&web_id=7184406560655279619",
            headers=self.http_headers,
            cookies=self.cookies,
            json={
                "category_ids": ["170"],
                "item_id": item_id,
                "item_type": 2,
                "topic_ids": []
            }
        )
        if publish_resp.status_code != 200:
            self.logger.error(f"publish post error: {publish_resp.text}")
        self.notify(f"每日发帖成功，获得 100 积分，动态链接：https://bbs.picoxr.com/post/{item_id}")

    def list_item_id_by_cat(self, catetory_id: str):
        posts = self.session.get(
            f"https://bbs.picoxr.com/ttarch/api/content/v1/content/list_by_pool_page?app_id=264482&page_size=20&page_index=1&pool_type=0&category_id={catetory_id}&item_type=2&sort_type=1&service_id=0&lang=zh-Hans-CN&web_id=7184406560655279619",
            cookies=self.cookies,
            headers=self.http_headers
        )
        if posts.status_code != 200:
            self.logger.error(f"list post error: {posts.text}")

        item_ids = []
        for item in posts.json()["data"]:
            item_ids.append(item["content"]["item_id"])

        return item_ids

    def comment(self):
        item_ids = self.list_item_id_by_cat("170")
        random_comments = [
            "666666",
            "厉害厉害",
            "收到",
            "可以可以"
        ]
        for item_id in item_ids:
            resp = self.session.post(
                "https://bbs.picoxr.com/ttarch/api/interact/v1/comment/create?app_id=264482&service_id=0&lang=zh-Hans-CN&web_id=7184406560655279619",
                json={
                    "comment": {
                        "item_type": 2,
                        "item_id": item_id,
                        "content": random.choice(random_comments),
                        "rec_list":[]
                    }
                },
                cookies=self.cookies,
                headers=self.http_headers,
            )
            if resp.status_code != 200:
                self.logger.warning(f"发送评论失败: {resp.text}")
                continue

            self.notify(f"评论成功，获得 5 积分，动态链接：https://bbs.picoxr.com/post/{item_id}")
            time.sleep(1.3)


class Echo(MsgChannel):
    def send(self, text: str):
        return print(text)


if __name__ == "__main__":
    cli = PicoBBS(session_id="<cookie 中的 sessionid 值>", channels=[
        Echo(),
        LarkChannel("<飞书 webhook>"),
    ])
    cli.sign()          # 执行每日签到
    cli.publish_post()  # 每日发帖
    cli.comment()       # 发送 20 个评论