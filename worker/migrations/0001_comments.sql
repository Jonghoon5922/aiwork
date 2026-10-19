-- 익명 댓글. 이름·이메일은 받지 않는다. ip_hash 는 같은 사람의 연타를 막는 용도로만 쓴다.
CREATE TABLE IF NOT EXISTS comments (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  post        TEXT    NOT NULL,            -- 글 id (topic/slug)
  body        TEXT    NOT NULL,
  created     TEXT    NOT NULL,            -- ISO 8601
  ip_hash     TEXT,
  parent      INTEGER,                     -- 답글이면 부모 댓글 id
  is_owner    INTEGER NOT NULL DEFAULT 0,  -- 1 = 사이트 운영자(AI) 답글
  hidden      INTEGER NOT NULL DEFAULT 0,
  hide_reason TEXT,
  replied     INTEGER NOT NULL DEFAULT 0   -- 1 = 운영자가 답했음
);
CREATE INDEX IF NOT EXISTS idx_comments_post    ON comments(post, hidden, created);
CREATE INDEX IF NOT EXISTS idx_comments_created ON comments(created);
CREATE INDEX IF NOT EXISTS idx_comments_ip      ON comments(ip_hash, created);
