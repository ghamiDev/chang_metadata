import streamlit as st
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
import random
import json
import base64
import shutil

# --- Cek ffmpeg di server
if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
    st.error("⚠️ FFmpeg belum terpasang di server. Tambahkan 'ffmpeg' di packages.txt atau install manual.")
    st.stop()

st.set_page_config(page_title="Auto Video Metadata Manager", page_icon="🎬", layout="centered")

st.title("🎬 Auto Video Metadata Cleaner & Random Rewriter")
st.caption("Upload video → tampilkan metadata lama → hapus → isi metadata baru otomatis & acak → download hasilnya")

# --- Fungsi untuk membaca metadata lama pakai ffprobe
def get_metadata(video_path: Path):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(video_path)
            ],
            capture_output=True,
            text=True
        )
        metadata = json.loads(result.stdout)
        return metadata.get("format", {}).get("tags", {})
    except Exception as e:
        return {"error": str(e)}

# --- Fungsi untuk membuat metadata acak baru
def generate_random_metadata(old_meta: dict):
    random_suffix = random.randint(1000, 9999)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def different(key, default):
        old_value = old_meta.get(key, "")
        new_value = f"{default}_{random_suffix}"
        return new_value if new_value != old_value else f"{default}_{random_suffix + 1}"

    return {
        "title": different("title", "AutoTitle"),
        "artist": different("artist", "AutoArtist"),
        "comment": f"Metadata replaced automatically at {now}",
        "copyright": f"© {datetime.now().year} AutoMetaSystem_{random_suffix}"
    }

# --- Fungsi preview video kecil
def get_base64_video(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

def small_video_preview(video_path):
    st.markdown(
        f"""
        <video width="320" height="180" controls>
            <source src="data:video/mp4;base64,{get_base64_video(video_path)}" type="video/mp4">
            Your browser does not support the video tag.
        </video>
        """,
        unsafe_allow_html=True
    )

# --- UI Upload
uploaded_file = st.file_uploader("📤 Upload video file", type=["mp4", "mov", "mkv"])

if uploaded_file:
    # Simpan file upload ke disk sementara
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_input_path = Path(tmp.name)

    # Tampilkan preview kecil
    small_video_preview(tmp_input_path)

    # Ambil metadata lama
    st.subheader("🔍 Original Metadata")
    old_metadata = get_metadata(tmp_input_path)
    if old_metadata:
        st.json(old_metadata)
    else:
        st.warning("Tidak ada metadata lama ditemukan.")

    # Buat metadata acak baru
    new_metadata = generate_random_metadata(old_metadata)
    st.subheader("🧠 Generated New Metadata (Auto & Random)")
    st.json(new_metadata)

    if st.button("🚀 Replace Metadata Now"):
        with st.spinner("Processing video... ⏳"):
            output_path = tmp_input_path.with_name("video_with_new_random_metadata.mp4")

            cmd = [
                "ffmpeg", "-y",
                "-i", str(tmp_input_path),
                "-map_metadata", "-1",
                "-metadata", f"title={new_metadata['title']}",
                "-metadata", f"artist={new_metadata['artist']}",
                "-metadata", f"comment={new_metadata['comment']}",
                "-metadata", f"copyright={new_metadata['copyright']}",
                "-codec", "copy", str(output_path)
            ]

            process = subprocess.run(cmd, capture_output=True, text=True)

            if process.returncode == 0 and output_path.exists():
                st.success("✅ Metadata berhasil diganti!")
                small_video_preview(output_path)

                st.subheader("📜 New Metadata Result")
                st.json(get_metadata(output_path))

                with open(output_path, "rb") as f:
                    st.download_button(
                        "💾 Download Updated Video",
                        data=f,
                        file_name="video_with_new_random_metadata.mp4",
                        mime="video/mp4"
                    )
            else:
                st.error("❌ Gagal mengubah metadata.")
                st.code(process.stderr, language="bash")

    # Simpan metadata log
    with open("metadata_log.json", "a") as f:
        json.dump({"old": old_metadata, "new": new_metadata}, f)
        f.write("\n")
