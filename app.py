from supabase import create_client

# 初始化 Supabase 客户端
url = "https://ofxbmmidmnqpuueyncqu.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9meGJtbWlkbW5xcHV1ZXluY3F1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDA4NjEwMjYsImV4cCI6MjA1NjQzNzAyNn0.qo7L6egD7Tl3l4lUOq8WnfwX2aL3Vuvec4UapZFBxbA"

client = create_client(url, key)

# 删除 `users` 表中的所有记录
client.table('users').delete().neq('id', '0').execute()

# 删除 `chat_history` 表中的所有记录
client.table('chat_history').delete().neq('id', '0').execute()