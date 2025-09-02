import streamlit as st
import os
import time
import io
import zipfile
from pdf2image import convert_from_path
from PyPDF2 import PdfReader

# ---------- State ----------
if "all_images" not in st.session_state:
    st.session_state.all_images = []
if "ringkasan" not in st.session_state:
    st.session_state.ringkasan = {"berhasil": 0, "gagal": 0, "skip": 0, "total": 0}
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0  # dipakai untuk reset uploader

def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:  # fallback versi lama
        st.experimental_rerun()

# ---------- Core ----------
def convert_with_retry(file_path, max_retries=3):
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    success = False
    images_out = []

    # cek password
    try:
        reader = PdfReader(file_path)
        if reader.is_encrypted:
            return None, "skip"
    except Exception as e:
        return None, f"error: {e}"

    for attempt in range(max_retries):
        try:
            # jangan pakai fmt="jpeg" agar nama file kita yang atur
            images = convert_from_path(file_path, dpi=200)
            for i, img in enumerate(images, start=1):
                buf = io.BytesIO()
                img.save(buf, format="JPEG")
                buf.seek(0)
                fname = f"{base_name}.jpeg" if i == 1 else f"{base_name}_{i}.jpeg"
                images_out.append((fname, buf.read()))
            success = True
            break
        except Exception:
            time.sleep(2)  # jeda lalu retry

    if success:
        return images_out, "ok"
    else:
        return None, "fail"

# ---------- UI ----------
st.title("📄 Konversi PDF ke JPEG")



# uploader dengan key dinamis supaya bisa direset
uploaded_files = st.file_uploader(
    "Upload file PDF", type=["pdf"], accept_multiple_files=True,
    key=f"uploader_{st.session_state.uploader_key}"
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        with st.spinner(f"Memproses {uploaded_file.name} ..."):
            # simpan file sementara pakai nama asli
            tmp_path = uploaded_file.name
            with open(tmp_path, "wb") as f:
                f.write(uploaded_file.read())

            result, status = convert_with_retry(tmp_path)

            if status == "ok":
                st.session_state.ringkasan["berhasil"] += 1
                st.success(f"Berhasil: {uploaded_file.name}")
                for fname, data in result:
                    st.image(data, caption=fname)
                    st.session_state.all_images.append((fname, data))
            elif status == "skip":
                st.session_state.ringkasan["skip"] += 1
                st.warning(f"SKIP (berpassword): {uploaded_file.name}")
            else:
                st.session_state.ringkasan["gagal"] += 1
                st.error(f"Gagal permanen: {uploaded_file.name}")

            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    st.session_state.ringkasan["total"] = (
        st.session_state.ringkasan["berhasil"]
        + st.session_state.ringkasan["gagal"]
        + st.session_state.ringkasan["skip"]
    )

# ---------- Ringkasan ----------
st.write("### 📊 Ringkasan")
st.write(f"✅ Berhasil : {st.session_state.ringkasan['berhasil']}")
st.write(f"❌ Gagal    : {st.session_state.ringkasan['gagal']}")
st.write(f"🔒 Skip     : {st.session_state.ringkasan['skip']}")
st.write(f"📄 Total    : {st.session_state.ringkasan['total']}")

# ---------- Download ZIP ----------
if st.session_state.all_images:
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as z:
        for fname, data in st.session_state.all_images:
            z.writestr(fname, data)
    zip_buf.seek(0)
    st.download_button(
        label="💾 Download Semua JPEG (ZIP)",
        data=zip_buf,
        file_name="hasil_konversi.zip",
        mime="application/zip"
    )
# tombol bersihkan (reset total)
col1, col2 = st.columns([1, 3])
with col1:
    if st.button("🗑️ Bersihkan Semua"):
        st.session_state.all_images = []
        st.session_state.ringkasan = {"berhasil": 0, "gagal": 0, "skip": 0, "total": 0}
        st.session_state.uploader_key += 1   # kunci: reset widget uploader
        _rerun()
# ---------- Kredit tetap di kiri bawah ----------
st.markdown(
    """
    <style>
    .kredit-fixed {
        position: fixed;
        left: 12px;
        bottom: 12px;
        z-index: 9999;
        color: rgba(100,100,100,0.9);
        font-size: 13px;
        background: rgba(255,255,255,0.6);
        padding: 4px 8px;
        border-radius: 6px;
        backdrop-filter: blur(4px);
        pointer-events: none;
    }
    </style>
    <div class="kredit-fixed">© 2025 Created by Tri 👩‍💻</div>
    """,
    unsafe_allow_html=True
)
