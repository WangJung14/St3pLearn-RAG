import os
import chromadb

# Đường dẫn lưu DB local
CHROMA_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")
CHROMA_DATA_PATH = os.path.abspath(CHROMA_DATA_PATH)

print(f"Đang kết nối tới ChromaDB tại: {CHROMA_DATA_PATH}")

try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
    collection = chroma_client.get_or_create_collection(name="course_knowledge")
    
    # Lấy toàn bộ dữ liệu trong collection
    results = collection.get(include=["documents", "metadatas"])
    
    total_chunks = len(results['ids'])
    print(f"\n✅ Kết nối thành công! Tổng số chunks hiện có trong DB: {total_chunks}")
    print("=" * 60)
    
    if total_chunks == 0:
        print("Cơ sở dữ liệu đang trống. Hãy thử nạp tài liệu từ giao diện trước.")
    else:
        # In ra tối đa 10 chunks đầu tiên để xem thử mẫu
        show_limit = min(10, total_chunks)
        print(f"Hiển thị {show_limit} chunks đầu tiên:")
        print("-" * 60)
        
        for i in range(show_limit):
            print(f"📌 [Chunk {i+1}/{total_chunks}]")
            print(f"🔑 ID: {results['ids'][i]}")
            print(f"ℹ️ Metadata: {results['metadatas'][i]}")
            # Cắt ngắn văn bản hiển thị cho gọn
            doc_snippet = results['documents'][i].replace('\n', ' ')
            if len(doc_snippet) > 150:
                doc_snippet = doc_snippet[:150] + "..."
            print(f"📝 Nội dung: {doc_snippet}")
            print("-" * 60)
            
        if total_chunks > 10:
            print(f"... và còn {total_chunks - 10} chunks khác trong Database.")
            
except Exception as e:
    print(f"❌ Có lỗi xảy ra khi đọc cơ sở dữ liệu: {e}")
