from math import ceil
import os
import time
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from post_store import (          
    get_all_posts,
    get_post,
    create_post,
    search_posts,
    update_post,
    delete_post,
    increment_views,
)
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "svg"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) #업로드 폴더가 없다면 생성
PER_PAGE = 10


def to_youtube_embed_url(youtube_url: str | None) -> str | None:
    """일반 유튜브 URL을 embed용 URL로 변환. 유효하지 않으면 None"""
    if not youtube_url:
        return None
    
    youtube_url = youtube_url.strip()
    if not youtube_url:
        return None
    
    parsed = urlparse(youtube_url)

    # 1) https://www.youtube.com/watch?v=VIDEO_ID 형식
    if "youtube.com" in parsed.netloc:
        qs = parse_qs(parsed.query)
        video_ids = qs.get("v")
        if video_ids:
            video_Id = video_ids[0]
            return f"https://www.youtube.com/embed/{video_Id}"
    
    # 2) https://youtu.be/VIDEO_ID 형식
    if "youtu.be" in parsed.netloc:
        # path 맨 앞의 "/" 제거
        video_id = parsed.path.lstrip("/")
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}"

    # 그 외는 일단 그대로 embed 시도 (아주 단순 fallback)
    return None


"""파일 이름이 허용된 확장자인지 확인"""
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------
# 라우트들
# ---------------------------

"""글 목록 페이지(검색 추가)"""
@app.route("/posts")
def posts_list():
    # 1) 쿼리 파라미터에서 검색어 & 정렬옵션 & 페이지 번호 가져오기
    query = request.args.get("q", "").strip()
    sort_option = request.args.get("sort", "recent") #arg에서 sort찾고 없으면 기본값: 최신순(recent)
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    if page < 1:
        page = 1

    # 2) 검색 결과 가져오기
    posts = search_posts(query)

    # 3) 정렬 분기
    if sort_option == "oldest":
        # 오래된순: id 오름차순
        sorted_posts = sorted(posts, key=lambda p: p["id"])
    elif sort_option == "views":
        # 조회수순: views 내림차순
        sorted_posts = sorted(posts, key=lambda p: p.get("views", 0), reverse=True)
    else:
        #기본(또는 sort_option이 이상한 값): 최신순
        sorted_posts = sorted(posts, key=lambda p: p["id"], reverse=True)
        sort_option = "recent" #엉뚱한 값 강제로 안전하게 정규화

    # 4) 페이지네이션 계산
    total_posts = len(sorted_posts)
    total_pages = max(1, ceil(total_posts / PER_PAGE))

    #page가 범위 밖이면 보정
    if page > total_pages:
        page = total_pages

    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    paginated_posts = sorted_posts[start:end]

    has_prev = page > 1
    has_next = page < total_pages

    # 4) templates에 검색어 & 정렬옵션 함께 넘겨줌    
    return render_template(
        "posts_list.html", 
        posts=sorted_posts, 
        query=query,
        sort_option=sort_option,
        page=page,
        total_pages=total_pages,
        has_prev=has_prev,
        has_next=has_next,
        )



"""글 상세 페이지 + 조회수 증가"""
@app.route("/posts/<int:post_id>")
def posts_detail(post_id):
    # 해당 id의 글 찾기
    post = increment_views(post_id)
    if post is None:
        return "게시글을 찾을 수 없습니다.", 404
    
    youtube_embed_url = to_youtube_embed_url(post.get("youtube_url"))

    return render_template("posts_detail.html", post=post, youtube_embed_url=youtube_embed_url)



"""새 글 작성 페이지 (GET: 폼, POST: 저장)"""
@app.route("/posts/new", methods=["GET", "POST"])
def posts_new():
    
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        author = request.form.get("author", "").strip() or "익명"
        image_url_input = request.form.get("image_url", "").strip() or None
        youtube_url_input = request.form.get("youtube_url", "").strip() or None

        #파일 객체 읽기
        file = request.files.get("image_file")
        #최종적으로 post에 들어갈 image_url 값
        final_image_url = None

        # 1) 파일이 있고, 이름이 있고, 허용 확장자라면 → 파일 업로드 우선
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = f"{int(time.time())}_{filename}"
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(save_path)

            #템플릿에서 바로 <img src="..."로 쓸 수 있는 경로
            final_image_url = f"/{UPLOAD_FOLDER}/{filename}"

        # 2) 파일 업로드가 없고, URL이 있다면 → URL 사용
        elif image_url_input:
            final_image_url = image_url_input

        # 3) 제목/내용 검증
        if not title or not content:
            return "제목과 내용은 필수입니다.", 400

         # 유튜브 URL은 원본을 저장 (필요할 때 embed로 변환)
        post = create_post(title, content, author, final_image_url, youtube_url_input)
        
        # 글 상세 페이지로 이동
        return redirect(url_for("posts_detail", post_id=post["id"]))

    # GET 요청이면 글 작성 폼 보여주기
    return render_template("posts_form.html", mode="new")



"""기존 글 수정 페이지"""
@app.route("/posts/<int:post_id>/edit", methods=["GET", "POST"])
def posts_edit(post_id):
    post = get_post(post_id)
    
    if post is None:
        return "게시글을 찾을 수 없습니다.", 404

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        author = request.form.get("author", "").strip() or "익명"
        image_url_input = request.form.get("image_url", "").strip() or None
        youtube_url_input = request.form.get("youtube_url", "").strip() or None

        file = request.files.get("image_file")
        #기본값: 기존 이미지 유지
        final_image_url = post.get("image_url")
        # 아주 단순 정책
        final_youtube_url = youtube_url_input or post.get("youtube_url")

        # 1) 새 파일이 올라왔다면 → 파일 기준으로 교체
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = f"{int(time.time())}_{filename}"
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(save_path)
            final_image_url = f"/{UPLOAD_FOLDER}/{filename}"

        # 2) 새 파일은 없고, URL 입력이 있다면 → URL로 덮어쓰기
        elif image_url_input:
            final_image_url = image_url_input

        # 3) 제목/내용 검증
        if not title or not content:
            return "제목과 내용은 필수입니다.", 400

        updated = update_post(post_id, title, content, author, final_image_url, final_youtube_url)
        if updated is None:
            return "수정 중 오류가 발생했습니다.", 500

        return redirect(url_for("posts_detail", post_id=post_id))

    # GET: 기존 값이 채워진 폼 보여주기
    return render_template("posts_form.html", mode="edit", post=post)



"""게시글 삭제"""
@app.route("/posts/<int:post_id>/delete", methods=["POST"])
def posts_delete_route(post_id):
    ok = delete_post(post_id)
    if not ok:
        return "이미 삭제되었거나 없는 게시글입니다.", 404
    
    return redirect(url_for("posts_list"))



# 편의를 위해 루트(/)에서 바로 /posts로 리다이렉트
@app.route("/")
def index():
    return redirect(url_for("posts_list"))


if __name__ == "__main__":
    app.run(debug=True)
