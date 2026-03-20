import { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import toast from "react-hot-toast";
import {
  Calendar, Check, FileVideo, Image as ImageIcon,
  Sparkles, Type, Upload, X, ChevronDown, ChevronUp,
} from "lucide-react";
import { generateCaption } from "../api/ai";
import { createPost, getRecommendations } from "../api/posts";
import { PLATFORMS, type PlatformMeta } from "../types";

const TONES = ["casual", "professional", "funny", "inspirational", "educational"];
const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "Hindi" },
  { code: "ta", label: "Tamil" },
  { code: "te", label: "Telugu" },
  { code: "bn", label: "Bangla" },
  { code: "mr", label: "Marathi" },
];

function supportsMedia(platform: PlatformMeta, mediaType: string) {
  if (mediaType === "video") return platform.supportsVideo;
  if (mediaType === "image") return platform.supportsImage;
  return platform.supportsText;
}

function mediaLabel(mediaType: string) {
  if (mediaType === "video") return "video";
  if (mediaType === "image") return "image";
  return "text";
}

function platformHint(platform: PlatformMeta, mediaType: string) {
  if (!supportsMedia(platform, mediaType))
    return `Not available for ${mediaLabel(mediaType)} posts`;
  if (mediaType === "video") return "Video publishing supported";
  if (mediaType === "image") return "Image publishing supported";
  return "Text publishing supported";
}

function localDateTimeValue(date = new Date()) {
  const offsetDate = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return offsetDate.toISOString().slice(0, 16);
}

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

  const mediaType = file
    ? file.type.startsWith("video") ? "video" : "image"
    : "text";
  const minScheduleValue = localDateTimeValue();

  const { data: recs = [] } = useQuery({
    queryKey: ["recs", mediaType, aiLang],
    queryFn: () =>
      getRecommendations(mediaType, 0, aiLang).then((r) => r.data.recommendations),
  });

  useEffect(() => {
    setSelectedPlatforms((prev) =>
      prev.filter((id) => {
        const p = PLATFORMS.find((item) => item.id === id);
        return p ? supportsMedia(p, mediaType) : false;
      })
    );
  }, [mediaType]);

  const aiMutation = useMutation({
    mutationFn: () =>
      generateCaption({
        topic: aiTopic,
        tone: aiTone,
        language: aiLang,
        media_type: mediaType,
        platforms: selectedPlatforms,
      }),
    onSuccess: (res) => {
      setCaption(res.data.caption);
      toast.success("Caption generated");
    },
    onError: () => toast.error("AI generation failed"),
  });

  const uploadMutation = useMutation({
    mutationFn: (form: FormData) => createPost(form),
    onSuccess: () => {
      toast.success("Post created and queued for distribution");
      qc.invalidateQueries({ queryKey: ["posts"] });
      setFile(null);
      setCaption("");
      setSelectedPlatforms([]);
      setTitle("");
      setScheduledAt("");
      setAiTopic("");
    },
    onError: () => toast.error("Upload failed"),
  });

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxFiles: 1,
    maxSize: 500 * 1024 * 1024,
    accept: { "image/*": [], "video/*": [] },
  });

  const togglePlatform = (id: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const recommendedIds = recs.slice(0, 5).map((r) => r.platform);
  const compatibleRecommendedIds = recommendedIds.filter((id) => {
    const p = PLATFORMS.find((item) => item.id === id);
    return p ? supportsMedia(p, mediaType) : false;
  });

  const handleSubmit = () => {
    if (selectedPlatforms.length === 0) {
      toast.error("Select at least one platform");
      return;
    }
    if (!caption.trim() && !file) {
      toast.error("Add a caption or upload media");
      return;
    }
    const form = new FormData();
    if (file) form.append("file", file);
    form.append("caption", caption.trim());
    form.append("title", title.trim());
    form.append("target_platforms", JSON.stringify(selectedPlatforms));
    if (scheduledAt) form.append("scheduled_at", scheduledAt);
    uploadMutation.mutate(form);
  };

  const handleGenerateCaption = () => {
    if (aiTopic.trim().length < 3) {
      toast.error("Prompt must be at least 3 characters");
      return;
    }
    aiMutation.mutate();
  };

  const canSubmit =
    selectedPlatforms.length > 0 &&
    (Boolean(file) || caption.trim().length > 0);

  const mediaTypeColor =
    mediaType === "video"
      ? "text-blue-300 border-blue-400/30 bg-blue-500/10"
      : mediaType === "image"
      ? "text-emerald-300 border-emerald-400/30 bg-emerald-500/10"
      : "text-purple-300 border-purple-400/30 bg-purple-500/10";

  return (
    <div className="mx-auto max-w-3xl w-full space-y-5 animate-fade-in">

      {/* ── Page header ── */}
      <div className="flex flex-col gap-1 pt-1">
        <h1 className="text-2xl font-bold text-white tracking-tight">Upload Content</h1>
        <p className="text-sm text-white/50">
          Upload once · select channels · publish or schedule from one place.
        </p>
      </div>

      {/* ── Section 1: Media ── */}
      <section className="card space-y-4">
        {/* Section header */}
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-white">Media</h2>
            <p className="text-xs text-white/40 mt-0.5">
              Drop a video or image, or leave empty for text-only.
            </p>
          </div>
          <span className={`badge border text-[11px] uppercase tracking-wider font-bold ${mediaTypeColor}`}>
            {mediaLabel(mediaType)}
          </span>
        </div>

        {/* Dropzone */}
        <div
          {...getRootProps({
            className: clsx(
              "rounded-2xl border-2 border-dashed p-6 text-center transition-all duration-200 cursor-pointer",
              isDragActive
                ? "border-brand-400/70 bg-brand-500/10"
                : "border-white/[0.09] bg-white/[0.025] hover:border-white/20 hover:bg-white/[0.045]"
            ),
          })}
        >
          <input {...getInputProps()} />
          {file ? (
            <div className="flex flex-col gap-3 text-left sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/10 text-white shrink-0">
                  {file.type.startsWith("video") ? <FileVideo size={22} /> : <ImageIcon size={22} />}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-white">{file.name}</p>
                  <p className="text-xs text-white/40">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
                </div>
              </div>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setFile(null); }}
                className="inline-flex items-center gap-1.5 self-start rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white/60 transition hover:bg-white/10 hover:text-white"
              >
                <X size={13} /> Remove
              </button>
            </div>
          ) : (
            <div className="space-y-2.5">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-white/[0.07] text-white/60">
                <Upload size={24} />
              </div>
              <div>
                <p className="text-sm font-semibold text-white">Drop your video or image here</p>
                <p className="text-xs text-white/40 mt-0.5">MP4, MOV, JPG, PNG up to 500 MB</p>
              </div>
            </div>
          )}
        </div>

        {/* Title + Caption
            Mobile:  stack (single column)
            Tablet (md 768px+): side by side, equal columns
            Desktop (lg 1024px+): title 1fr, caption 2fr
        */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-[1fr_2fr]">
          {/* Title */}
          <div className="space-y-1.5">
            <label
              className="text-xs font-semibold text-white/60 uppercase tracking-wide"
              htmlFor="post-title"
            >
              Title
            </label>
            <input
              id="post-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Campaign name"
              className="input"
            />
          </div>

          {/* Caption */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between gap-2">
              <label
                className="text-xs font-semibold text-white/60 uppercase tracking-wide"
                htmlFor="post-caption"
              >
                Caption
              </label>
              <button
                type="button"
                onClick={() => setShowAI((v) => !v)}
                className={clsx(
                  "inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all shrink-0",
                  showAI
                    ? "bg-brand-500/20 text-brand-200 border border-brand-400/30"
                    : "text-brand-300 hover:text-white"
                )}
              >
                <Sparkles size={12} />
                {showAI ? "Hide AI" : "Generate with AI"}
                {showAI ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
              </button>
            </div>
            <textarea
              id="post-caption"
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              rows={4}
              placeholder="Write your caption or use AI to draft…"
              className="input min-h-[7rem] resize-y"
            />
          </div>
        </div>

        {/* AI Panel */}
        {showAI && (
          <div className="rounded-2xl border border-brand-400/20 bg-gradient-to-br from-brand-500/10 to-purple-600/5 p-5 space-y-4 animate-scale-in">
            <div className="flex items-center gap-2">
              <Sparkles size={14} className="text-brand-300" />
              <p className="text-sm font-semibold text-white">AI Caption Generator</p>
            </div>

            <div className="space-y-1.5">
              <label
                className="text-xs font-semibold text-white/60 uppercase tracking-wide"
                htmlFor="ai-topic"
              >
                Prompt
              </label>
              <input
                id="ai-topic"
                value={aiTopic}
                onChange={(e) => setAiTopic(e.target.value)}
                placeholder="Describe the content, audience, or campaign goal"
                className="input"
              />
            </div>

            {/* Tone + Language — stack on mobile, side by side on sm+ */}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <p className="text-xs font-semibold text-white/60 uppercase tracking-wide">Tone</p>
                <div className="flex flex-wrap gap-1.5">
                  {TONES.map((tone) => (
                    <button
                      key={tone}
                      type="button"
                      onClick={() => setAiTone(tone)}
                      className={clsx(
                        "rounded-lg border px-3 py-1.5 text-xs font-semibold capitalize transition-all",
                        aiTone === tone
                          ? "border-brand-400/50 bg-brand-500/20 text-white"
                          : "border-white/[0.09] bg-white/5 text-white/55 hover:border-white/20 hover:text-white"
                      )}
                    >
                      {tone}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-xs font-semibold text-white/60 uppercase tracking-wide">Language</p>
                <div className="flex flex-wrap gap-1.5">
                  {LANGUAGES.map((lang) => (
                    <button
                      key={lang.code}
                      type="button"
                      onClick={() => setAiLang(lang.code)}
                      className={clsx(
                        "rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all",
                        aiLang === lang.code
                          ? "border-brand-400/50 bg-brand-500/20 text-white"
                          : "border-white/[0.09] bg-white/5 text-white/55 hover:border-white/20 hover:text-white"
                      )}
                    >
                      {lang.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={handleGenerateCaption}
              disabled={aiTopic.trim().length < 3 || aiMutation.isPending}
              className="btn-primary w-full"
            >
              {aiMutation.isPending ? (
                <><span className="inline-block animate-spin">⟳</span> Generating…</>
              ) : (
                <><Sparkles size={14} /> Generate caption</>
              )}
            </button>
          </div>
        )}
      </section>

      {/* ── Section 2: Platforms ── */}
      <section className="card space-y-4">
        {/* Section header */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-white">Platforms</h2>
            <p className="text-xs text-white/40 mt-0.5">
              Only compatible platforms can be selected for {mediaLabel(mediaType)} posts.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="badge border border-white/10 bg-white/[0.06] text-white/60 text-[11px]">
              {selectedPlatforms.length} selected
            </span>
            {compatibleRecommendedIds.length > 0 && (
              <button
                type="button"
                onClick={() => setSelectedPlatforms(compatibleRecommendedIds)}
                className="rounded-lg border border-brand-400/30 bg-brand-500/10 px-2.5 py-1 text-xs font-semibold text-brand-200 transition hover:bg-brand-500/20"
              >
                Use recommended
              </button>
            )}
            {selectedPlatforms.length > 0 && (
              <button
                type="button"
                onClick={() => setSelectedPlatforms([])}
                className="rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-xs font-semibold text-white/50 transition hover:text-white"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Recommended badges */}
        {recs.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {recs.slice(0, 3).map((r) => (
              <span
                key={r.platform}
                className="badge border border-brand-400/20 bg-brand-500/10 text-brand-200 text-[11px]"
              >
                ✦ {PLATFORMS.find((p) => p.id === r.platform)?.name ?? r.platform}
              </span>
            ))}
          </div>
        )}

        {/* Platform chips grid
            Mobile (< 640px):  1 column
            Tablet (sm 640px+): 2 columns
            Desktop (xl 1280px+): 3 columns
        */}
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {PLATFORMS.map((platform) => {
            const isSelected = selectedPlatforms.includes(platform.id);
            const isRecommended = compatibleRecommendedIds.includes(platform.id);
            const isSupported = supportsMedia(platform, mediaType);

            return (
              <button
                key={platform.id}
                type="button"
                aria-pressed={isSelected}
                disabled={!isSupported}
                onClick={() => { if (isSupported) togglePlatform(platform.id); }}
                className={clsx(
                  "platform-chip w-full items-start justify-between text-left",
                  isSupported
                    ? isSelected ? "platform-chip-on" : "platform-chip-off"
                    : "platform-chip-disabled"
                )}
              >
                <span className="flex min-w-0 items-start gap-2.5">
                  <span className="mt-0.5 text-base shrink-0">{platform.icon}</span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm">{platform.name}</span>
                    <span className="mt-0.5 block text-[11px] font-normal text-white/40">
                      {platformHint(platform, mediaType)}
                    </span>
                  </span>
                </span>
                <span className="flex shrink-0 items-center gap-1.5 pl-2">
                  {isRecommended && !isSelected && isSupported && (
                    <span className="rounded-md bg-brand-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-brand-200">
                      Pick
                    </span>
                  )}
                  {isSelected && <Check size={15} className="text-brand-200" />}
                </span>
              </button>
            );
          })}
        </div>

        {/* Schedule row */}
        <div className="border-t border-white/[0.08] pt-4 space-y-2">
          <label
            className="text-xs font-semibold text-white/60 uppercase tracking-wide"
            htmlFor="schedule-at"
          >
            Schedule (optional)
          </label>
          <div className="flex items-center gap-2">
            <Calendar size={15} className="shrink-0 text-white/35" />
            <input
              id="schedule-at"
              type="datetime-local"
              min={minScheduleValue}
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              className="input flex-1 min-w-0"
            />
            {scheduledAt && (
              <button
                type="button"
                onClick={() => setScheduledAt("")}
                className="rounded-lg border border-white/10 bg-white/5 p-2.5 text-white/45 transition hover:bg-white/10 hover:text-white tap-target flex items-center justify-center shrink-0"
              >
                <X size={14} />
              </button>
            )}
          </div>
          <p className="text-xs text-white/35">Leave empty to publish immediately.</p>
        </div>
      </section>

      {/* ── Submit ── */}
      <button
        type="button"
        onClick={handleSubmit}
        disabled={uploadMutation.isPending || !canSubmit}
        className="btn-primary w-full py-3.5 text-base"
      >
        {uploadMutation.isPending ? (
          <><span className="inline-block animate-spin">⟳</span> Submitting…</>
        ) : scheduledAt ? (
          <><Calendar size={18} /> Schedule post</>
        ) : (
          <><Upload size={18} /> Publish now</>
        )}
      </button>

      {/* Legend */}
      <div className="flex flex-wrap items-center justify-center gap-4 pb-2 opacity-45">
        {[
          { icon: FileVideo, label: "Video supports",  color: "text-blue-300" },
          { icon: ImageIcon, label: "Image supports",  color: "text-emerald-300" },
          { icon: Type,      label: "Text supports",   color: "text-purple-300" },
        ].map(({ icon: Icon, label, color }) => (
          <div key={label} className="flex items-center gap-1.5 text-xs text-white/40">
            <Icon size={13} className={color} />
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}
