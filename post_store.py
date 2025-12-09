import os
import json
from datetime import datetime

DATA_FILE = "posts_data.json"

# 모듈이 import될 때 한 번만 데이터 로드
"""JSON 파일에서 posts와 next_id를 읽어온다."""
def load_data():
    if not os.path.exists(DATA_FILE):
        # 파일이 없으면 빈 목록과 next_id = 1 반환
        return [], 1
    
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    posts = data.get("posts", [])
    next_id = data.get("next_id", 1)

    #혹시 예전 데이터에 필요한 필드가 빠져있을 수 있으니 기본값 채우기
    for p in posts:
        if "views" not in p:
            p["views"] = 0
        if "image_url" not in p:
            p["image_url"] = None
        if "updated_at" not in p:
            p["updated_at"] = None
        if "youtube_url" not in p:
            p["youtube_url"] = None


    return posts, next_id


"""posts와 next_id를 JSON 파일에 저장한다."""
def save_data(posts, next_id):
    data = {
        "posts": posts,
        "next_id": next_id
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# 🔹 이 모듈이 "데이터의 집" 역할을 한다
_posts, _next_id = load_data()


# ─────────────────────────────
#  기본 조회 / 유틸 함수들
# ─────────────────────────────

def get_all_posts():
    """현재 저장된 모든 게시글 리스트를 반환 (읽기 전용)"""
    return _posts

def get_post(post_id: int):
    """id로 게시글 하나 찾기. 없으면 None."""
    return next((p for p in _posts if p["id"] == post_id), None)


# ─────────────────────────────
#  생성 / 수정 / 삭제 / 조회수
# ─────────────────────────────

""" 
    새 게시글을 생성
    내부 리스트에 추가-JSON에 저장
    생성된 post 딕셔너리를 반환
"""
def create_post(title: str, content: str, author: str,
                image_url: str | None, youtube_url: str | None):
    global _next_id
    post = {
        "id": _next_id,
        "title": title,
        "content": content,
        "author": author,
        "image_url": image_url,  # 이미지 URL (선택)
        "youtube_url": youtube_url,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "updated_at": None,
        "views": 0,
    }

    _posts.append(post)
    _next_id += 1
    save_data(_posts, _next_id)

    return post


"""
    기존 게시글 수정+저장
    수정된 post 반환
"""
def update_post(post_id: int, title: str, content: str, author: str,
                image_url: str | None, youtube_url: str | None):

    post = get_post(post_id)

    if post is None:
        return None
    
    post["title"] = title
    post["content"] = content
    post["author"] = author
    post["image_url"] = image_url
    post["youtube_url"] = youtube_url
    post["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    save_data(_posts, _next_id)
    return post


"""
    게시글 삭제 후 저장. 성공하면 True, 없으면 False.
"""
def delete_post(post_id: int):

    global _posts

    before = len(_posts)
    _posts = [p for p in _posts if p["id"] != post_id]
    after = len(_posts)

    if before != after:
        save_data(_posts, _next_id)
        return True
    return False


"""
    조회수 +1, 저장
"""
def increment_views(post_id: int):

    post = get_post(post_id)
    if post is None:
        return None
    
    post["views"] += 1
    save_data(_posts, _next_id)
    return post


"""
    검색어(query)가 제목이나 내용에 포함된 게시글만 필터링해 반환.
"""
def search_posts(query: str):
    if not query:
        return _posts
    
    q = query.lower()
    return [
        p for p in _posts
        if q in p["title"].lower() or q in p["content"].lower()
    ]