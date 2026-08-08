import { useEffect, useRef, useState } from "react";
import { Camera, Trash2 } from "lucide-react";
import api from "../../api/axios";
import toast from "react-hot-toast";
import OrgLogo from "./OrgLogo";
import ConfirmationModal from "./ConfirmationModal";

export default function OrgBanner({ orgId, orgName, bannerUrl, onBannerChange }) {
  const [preview, setPreview] = useState(bannerUrl || null);
  const [imgError, setImgError] = useState(false);
  const [loading, setLoading] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    setPreview(bannerUrl || null);
    setImgError(false);
  }, [bannerUrl]);

  const handleUpload = async (file) => {
    const formData = new FormData();
    formData.append("banner", file);
    setLoading(true);
    setImgError(false);

    try {
      const res = await api.post(`/org/${orgId}/banner`, formData);
      const url = `${res.data.banner_url}?t=${Date.now()}`;
      setPreview(url);
      onBannerChange?.(res.data.banner_url);
      toast.success("Club logo updated");
    } catch {
      toast.error("Upload failed");
      setPreview(bannerUrl || null);
    }

    setLoading(false);
  };

  const onFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPreview(URL.createObjectURL(file));
    setImgError(false);
    handleUpload(file);
    e.target.value = "";
  };

  const confirmRemove = async () => {
    setRemoving(true);
    try {
      await api.delete(`/org/${orgId}/banner`);
      setPreview(null);
      setImgError(false);
      onBannerChange?.("");
      toast.success("Club logo removed");
      setConfirmOpen(false);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to remove logo");
    }
    setRemoving(false);
  };

  const showImage = Boolean(preview) && !imgError;
  const busy = loading || removing;

  return (
    <>
      <div className="org-logo-wrap">
        <button
          type="button"
          className="org-logo-btn"
          onClick={() => !busy && inputRef.current?.click()}
          title="Change club logo"
          disabled={busy}
        >
          <div className={`org-logo-frame ${showImage ? "has-image" : ""}`}>
            {busy ? (
              <div className="org-logo-spinner" />
            ) : showImage ? (
              <img
                src={preview}
                alt={`${orgName || "Club"} logo`}
                onError={() => setImgError(true)}
              />
            ) : (
              <OrgLogo orgName={orgName} size={88} />
            )}
            {!busy && (
              <span className="org-logo-overlay">
                <Camera size={18} strokeWidth={2} />
                <span>{showImage ? "Change" : "Upload"}</span>
              </span>
            )}
          </div>
        </button>

        {showImage && !busy && (
          <button
            type="button"
            className="org-logo-remove"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setConfirmOpen(true);
            }}
            title="Remove logo"
            aria-label="Remove club logo"
          >
            <Trash2 size={14} strokeWidth={2} />
          </button>
        )}

        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg,image/jpg"
          className="d-none"
          onChange={onFileChange}
        />
      </div>

      <ConfirmationModal
        isOpen={confirmOpen}
        onClose={() => !removing && setConfirmOpen(false)}
        onConfirm={confirmRemove}
        title="Remove logo?"
        message="Remove this club logo?"
        isLoading={removing}
      />
    </>
  );
}
