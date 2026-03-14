import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { createPost } from "../api/posts";
import { generateCaption } from "../api/ai";
import { getRecommendations } from "../api/posts";
import { PLATFORMS } from "../types";
import toast from "react-hot-toast";
import clsx from "clsx";
import { Upload, Sparkles, X, Calendar } from "lucide-react";

const TONES = ["casual","professional","funny","inspirational","educational"];
const LANGUAGES = [
  { code: "en", label: "English" }, { code: "hi", label: "हिंदी" },
  { code: "ta", label: "தமிழ்"  }, { code: "te", label: "తెలుగు" },
  { code: "bn", label: "বাংলা"  }, { code: "mr", label: "मराठी"  },
];

export default function UploadPage() {
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [caption, setCaption] = useState("");
  const [title, setTitle] = useState("");
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [scheduledAt, setScheduledAt] = useState("");
  const [aiTopic, setAiTopic] = useState("");
  const [aiTone, setAiTone] = useState("casual");
  const [aiLang, setAiLang] = useState("en");
  const [showAI, setShowAI] = useState(false);

  const mediaType = file ? (file.type.startsWith("video") ? "video" : "image") : "text";

  const { data: recs } = useQuery({
    queryKey: ["recs", mediaType, aiLang],
    queryFn: () => getRecommendations(mediaType, 0, aiLang).then(r => r.data.recommendations),
    enabled: true,
  });

  const aiMutation = useMutation({
    mutationFn: () => generateCaption({ topic: aiTopic, tone: aiTone, language: aiLang, media_type: mediaType, platforms: selectedPlatforms }),
    onSuccess: (r) => { setCaption(r.data.caption); toast.success("Caption generated!"); },
    onError: () => toast.error("AI generation failed"),
  });

  const uploadMutation = useMutation({
    mutationFn: (form: FormData) => createPost(form),
    onSuccess: () => {
      toast.success("Post created and queued for distribution!");
      qc.invalidateQueries({ queryKey: ["posts"] });
      setFile(null); setCaption(""); setSelectedPlatforms([]); setTitle("");
    },
    onError: () => toast.error("Upload failed"),
  });

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, maxSize: 500 * 1024 * 1024,
    accept: { "image/*": [], "video/*": [] },
  });

  const togglePlatform = (id: string) => {
    setSelectedPlatforms(prev =>
      prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
    );
  };

  const handleSubmit = () => {
    if (selectedPlatforms.length === 0) return toast.error("Select at least one platform");
    if (!caption && !file) return toast.error("Add a caption or upload media");
    const form = new FormData();
    if (file) form.append("file", file);
    form.append("caption", caption);
    form.append("title", title);
    form.append("target_platforms", JSON.stringify(selectedPlatforms));
    if (scheduledAt) form.append("scheduled_at", scheduledAt);
    uploadMutation.mutate(form);
  };

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-5 animate-slide-up">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Upload Content</h1>
        <p className="text-slate-500 text-sm mt-1">Upload once, distribute everywhere</p>
      </div>

      {/* Drop Zone */}
      <div {...getRootProps()} className={clsx(
        "border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all duration-150",
        isDragActive ? "border-brand-400 bg-brand-50" : "border-slate-200 hover:border-brand-300 hover:bg-slate-50"
      )}>
        <input {...getInputProps()} />
        {file ? (
          <div className="flex items-center justify-center gap-3">
            <div className="text-3xl">{file.type.startsWith("video") ? "🎥" : "📷"}</div>
            <div className="text-left">
              <p className="font-medium text-slate-700">{file.name}</p>
              <p className="text-xs text-slate-400">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
            </div>
            <button onClick={(e) => { e.stopPropagation(); setFile(null); }} className="ml-2 text-slate-400 hover:text-red-500">
              <X size={18} />
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <Upload size={36} className="mx-auto text-slate-300" />
            <p className="text-slate-500 font-medium">Drop your video or image here</p>
            <p className="text-slate-400 text-sm">MP4, MOV, JPG, PNG — up to 500 MB</p>
          </div>
        )}
      </div>

      {/* Title */}
      <input value={title} onChange={e => setTitle(e.target.value)}
        placeholder="Video title (optional)" className="input" />

      {/* Caption + AI */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-slate-600">Caption</label>
          <button onClick={() => setShowAI(!showAI)}
            className="flex items-center gap-1.5 text-xs text-brand-600 hover:text-brand-800 font-medium">
            <Sparkles size={14} />
            {showAI ? "Hide AI" : "Generate with AI"}
          </button>
        </div>

        {showAI && (
          <div className="card p-4 space-y-3 border-brand-100 bg-gradient-to-br from-brand-50 to-purple-50">
            <input value={aiTopic} onChange={e => setAiTopic(e.target.value)}
              placeholder="What is your content about? e.g. new product launch for a skincare brand"
              className="input bg-white" />
            <div className="flex gap-2 flex-wrap">
              {TONES.map(t => (
                <button key={t} onClick={() => setAiTone(t)}
                  className={clsx("px-3 py-1 rounded-lg text-xs font-medium border transition-all",
                    aiTone === t ? "bg-brand-600 text-white border-brand-600" : "bg-white text-slate-500 border-slate-200 hover:border-brand-300")}>
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>
            <div className="flex gap-2 flex-wrap">
              {LANGUAGES.map(l => (
                <button key={l.code} onClick={() => setAiLang(l.code)}
                  className={clsx("px-2.5 py-1 rounded-lg text-xs border transition-all",
                    aiLang === l.code ? "bg-brand-600 text-white border-brand-600" : "bg-white text-slate-400 border-slate-200")}>
                  {l.label}
                </button>
              ))}
            </div>
            <button onClick={() => aiMutation.mutate()} disabled={!aiTopic || aiMutation.isPending}
              className="btn-primary w-full text-sm py-2">
              {aiMutation.isPending ? "✨ Generating..." : "✨ Generate Caption"}
            </button>
          </div>
        )}

        <textarea value={caption} onChange={e => setCaption(e.target.value)} rows={4}
          placeholder="Write your caption..." className="input resize-none" />
      </div>

      {/* Platform Selection */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-slate-600">Select Platforms</label>
          {recs && recs.length > 0 && (
            <span className="text-xs text-brand-600 font-medium">
              Recommended: {recs.slice(0,3).map(r => r.platform).join(", ")}
            </span>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {PLATFORMS.map((p) => {
            const isSelected = selectedPlatforms.includes(p.id);
            const isRecommended = recs?.slice(0,5).some(r => r.platform === p.id);
            return (
              <button key={p.id} onClick={() => togglePlatform(p.id)}
                className={clsx("platform-chip relative", isSelected ? "platform-chip-on" : "platform-chip-off")}>
                {isRecommended && !isSelected && (
                  <span className="absolute -top-1 -right-1 w-2 h-2 bg-brand-400 rounded-full" />
                )}
                <span>{p.icon}</span>
                <span>{p.name}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Schedule */}
      <div className="flex items-center gap-3">
        <Calendar size={16} className="text-slate-400" />
        <input type="datetime-local" value={scheduledAt} onChange={e => setScheduledAt(e.target.value)}
          className="input flex-1" />
        {scheduledAt && (
          <button onClick={() => setScheduledAt("")} className="text-slate-400 hover:text-red-500">
            <X size={16} />
          </button>
        )}
      </div>

      <button onClick={handleSubmit} disabled={uploadMutation.isPending}
        className="btn-primary w-full py-3 text-base">
        {uploadMutation.isPending ? "Uploading..." : scheduledAt ? "📅 Schedule Post" : "🚀 Publish Now"}
      </button>
    </div>
  );
}