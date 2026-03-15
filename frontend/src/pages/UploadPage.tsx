import { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import toast from "react-hot-toast";
import {
  Calendar,
  Check,
  FileVideo,
  Image as ImageIcon,
  Sparkles,
  Type,
  Upload,
  X,
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
  if (!supportsMedia(platform, mediaType)) {
    return `Not available for ${mediaLabel(mediaType)} posts`;
  }

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

  const mediaType = file ? (file.type.startsWith("video") ? "video" : "image") : "text";
  const minScheduleValue = localDateTimeValue();

  const { data: recs = [] } = useQuery({
    queryKey: ["recs", mediaType, aiLang],
    queryFn: () => getRecommendations(mediaType, 0, aiLang).then((response) => response.data.recommendations),
  });

  useEffect(() => {
    setSelectedPlatforms((previous) =>
      previous.filter((platformId) => {
        const platform = PLATFORMS.find((item) => item.id === platformId);
        return platform ? supportsMedia(platform, mediaType) : false;
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
    onSuccess: (response) => {
      setCaption(response.data.caption);
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
    if (accepted[0]) {
      setFile(accepted[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxFiles: 1,
    maxSize: 500 * 1024 * 1024,
    accept: { "image/*": [], "video/*": [] },
  });

  const togglePlatform = (id: string) => {
    setSelectedPlatforms((previous) =>
      previous.includes(id) ? previous.filter((platformId) => platformId !== id) : [...previous, id]
    );
  };

  const recommendedIds = recs.slice(0, 5).map((item) => item.platform);
  const compatibleRecommendedIds = recommendedIds.filter((platformId) => {
    const platform = PLATFORMS.find((item) => item.id === platformId);
    return platform ? supportsMedia(platform, mediaType) : false;
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

  const canSubmit = selectedPlatforms.length > 0 && (Boolean(file) || caption.trim().length > 0);

  return (
    <div className="mx-auto max-w-4xl space-y-6 animate-slide-up">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold text-white">Upload Content</h1>
        <p className="text-sm text-white/60">
          Upload once, select the right channels, and publish or schedule from one place.
        </p>
      </header>

      <section className="card space-y-5 p-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-white">Media</h2>
            <p className="text-sm text-white/[0.55]">Drop a video or image, or leave it empty for a text-only post.</p>
          </div>
          <span className="badge border border-white/10 bg-white/5 text-white/70 uppercase tracking-[0.2em]">
            {mediaLabel(mediaType)}
          </span>
        </div>

        <div
          {...getRootProps({
            className: clsx(
              "rounded-[1.75rem] border-2 border-dashed p-8 text-center transition-all duration-200",
              isDragActive
                ? "border-brand-300 bg-brand-500/10"
                : "border-white/10 bg-white/[0.03] hover:border-white/20 hover:bg-white/[0.05]"
            ),
          })}
        >
          <input {...getInputProps()} />
          {file ? (
            <div className="flex flex-col gap-4 text-left sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/10 text-white">
                  {file.type.startsWith("video") ? <FileVideo size={24} /> : <ImageIcon size={24} />}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-base font-semibold text-white">{file.name}</p>
                  <p className="text-sm text-white/50">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
                </div>
              </div>
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  setFile(null);
                }}
                className="inline-flex items-center justify-center gap-2 self-start rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/70 transition hover:bg-white/10 hover:text-white"
              >
                <X size={16} />
                Remove file
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl bg-white/10 text-white/80">
                <Upload size={28} />
              </div>
              <div className="space-y-1">
                <p className="text-base font-semibold text-white">Drop your video or image here</p>
                <p className="text-sm text-white/50">MP4, MOV, JPG, PNG up to 500 MB</p>
              </div>
            </div>
          )}
        </div>

        <div className="grid gap-4 lg:grid-cols-[1.1fr_1.9fr]">
          <div className="space-y-2">
            <label className="text-sm font-medium text-white/75" htmlFor="post-title">
              Title
            </label>
            <input
              id="post-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Video title or campaign name"
              className="input"
            />
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <label className="text-sm font-medium text-white/75" htmlFor="post-caption">
                Caption
              </label>
              <button
                type="button"
                onClick={() => setShowAI((value) => !value)}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-200 transition hover:text-white"
              >
                <Sparkles size={14} />
                {showAI ? "Hide AI tools" : "Generate with AI"}
              </button>
            </div>
            <textarea
              id="post-caption"
              value={caption}
              onChange={(event) => setCaption(event.target.value)}
              rows={5}
              placeholder="Write your caption or leave this for AI to draft."
              className="input min-h-[9rem] resize-y"
            />
          </div>
        </div>

        {showAI && (
          <div className="rounded-[1.75rem] border border-brand-300/20 bg-gradient-to-br from-brand-500/10 to-orange-400/10 p-5">
            <div className="flex flex-col gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-white/80" htmlFor="ai-topic">
                  Prompt
                </label>
                <input
                  id="ai-topic"
                  value={aiTopic}
                  onChange={(event) => setAiTopic(event.target.value)}
                  placeholder="Describe the content, audience, or campaign goal"
                  className="input"
                />
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium text-white/80">Tone</p>
                <div className="flex flex-wrap gap-2">
                  {TONES.map((tone) => (
                    <button
                      key={tone}
                      type="button"
                      onClick={() => setAiTone(tone)}
                      className={clsx(
                        "rounded-xl border px-3 py-2 text-xs font-semibold capitalize transition-all",
                        aiTone === tone
                          ? "border-brand-300/60 bg-brand-500/20 text-white"
                          : "border-white/10 bg-white/5 text-white/[0.65] hover:border-white/20 hover:text-white"
                      )}
                    >
                      {tone}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium text-white/80">Language</p>
                <div className="flex flex-wrap gap-2">
                  {LANGUAGES.map((language) => (
                    <button
                      key={language.code}
                      type="button"
                      onClick={() => setAiLang(language.code)}
                      className={clsx(
                        "rounded-xl border px-3 py-2 text-xs font-semibold transition-all",
                        aiLang === language.code
                          ? "border-brand-300/60 bg-brand-500/20 text-white"
                          : "border-white/10 bg-white/5 text-white/[0.65] hover:border-white/20 hover:text-white"
                      )}
                    >
                      {language.label}
                    </button>
                  ))}
                </div>
              </div>

              <button
                type="button"
                onClick={() => aiMutation.mutate()}
                disabled={!aiTopic.trim() || aiMutation.isPending}
                className="btn-primary w-full"
              >
                {aiMutation.isPending ? "Generating caption..." : "Generate caption"}
              </button>
            </div>
          </div>
        )}
      </section>

      <section className="card space-y-5 p-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Platforms</h2>
            <p className="text-sm text-white/[0.55]">
              Only compatible platforms can be selected for {mediaLabel(mediaType)} posts.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="badge border border-white/10 bg-white/5 text-white/70">
              {selectedPlatforms.length} selected
            </span>
            {compatibleRecommendedIds.length > 0 && (
              <button
                type="button"
                onClick={() => setSelectedPlatforms(compatibleRecommendedIds)}
                className="rounded-full border border-brand-300/30 bg-brand-500/10 px-3 py-1.5 text-xs font-semibold text-brand-100 transition hover:bg-brand-500/20"
              >
                Use recommended
              </button>
            )}
            {selectedPlatforms.length > 0 && (
              <button
                type="button"
                onClick={() => setSelectedPlatforms([])}
                className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold text-white/[0.65] transition hover:bg-white/10 hover:text-white"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {recs.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {recs.slice(0, 3).map((item) => (
              <span key={item.platform} className="badge border border-brand-300/20 bg-brand-500/10 text-brand-100">
                Recommended: {PLATFORMS.find((platform) => platform.id === item.platform)?.name ?? item.platform}
              </span>
            ))}
          </div>
        )}

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
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
                onClick={() => {
                  if (isSupported) togglePlatform(platform.id);
                }}
                className={clsx(
                  "platform-chip w-full items-start justify-between text-left",
                  isSupported ? (isSelected ? "platform-chip-on" : "platform-chip-off") : "platform-chip-disabled"
                )}
              >
                <span className="flex min-w-0 items-start gap-3">
                  <span className="mt-0.5 text-base">{platform.icon}</span>
                  <span className="min-w-0">
                    <span className="block truncate">{platform.name}</span>
                    <span className="mt-1 block text-xs font-normal text-white/50">
                      {platformHint(platform, mediaType)}
                    </span>
                  </span>
                </span>
                <span className="flex shrink-0 items-center gap-2 pl-3">
                  {isRecommended && !isSelected && isSupported && (
                    <span className="rounded-full bg-brand-400/20 px-2 py-1 text-[11px] font-semibold text-brand-100">
                      Pick
                    </span>
                  )}
                  {isSelected && <Check size={16} className="text-brand-100" />}
                </span>
              </button>
            );
          })}
        </div>

        <div className="grid gap-4 border-t border-white/10 pt-5 lg:grid-cols-[1fr_auto] lg:items-end">
          <div className="space-y-2">
            <label className="text-sm font-medium text-white/75" htmlFor="schedule-at">
              Schedule
            </label>
            <div className="flex items-center gap-3">
              <Calendar size={16} className="shrink-0 text-white/[0.45]" />
              <input
                id="schedule-at"
                type="datetime-local"
                min={minScheduleValue}
                value={scheduledAt}
                onChange={(event) => setScheduledAt(event.target.value)}
                className="input flex-1"
              />
              {scheduledAt && (
                <button
                  type="button"
                  onClick={() => setScheduledAt("")}
                  className="rounded-xl border border-white/10 bg-white/5 p-3 text-white/[0.55] transition hover:bg-white/10 hover:text-white"
                >
                  <X size={16} />
                </button>
              )}
            </div>
            <p className="text-xs text-white/[0.45]">Leave empty to publish immediately.</p>
          </div>

          <div className="grid grid-cols-3 gap-2 rounded-2xl border border-white/10 bg-white/[0.03] p-3">
            <div className="rounded-xl bg-white/5 p-3 text-center">
              <FileVideo size={16} className="mx-auto text-white/70" />
              <p className="mt-2 text-xs text-white/50">Video</p>
            </div>
            <div className="rounded-xl bg-white/5 p-3 text-center">
              <ImageIcon size={16} className="mx-auto text-white/70" />
              <p className="mt-2 text-xs text-white/50">Image</p>
            </div>
            <div className="rounded-xl bg-white/5 p-3 text-center">
              <Type size={16} className="mx-auto text-white/70" />
              <p className="mt-2 text-xs text-white/50">Text</p>
            </div>
          </div>
        </div>
      </section>

      <button
        type="button"
        onClick={handleSubmit}
        disabled={uploadMutation.isPending || !canSubmit}
        className="btn-primary w-full py-4 text-base disabled:opacity-50"
      >
        {uploadMutation.isPending ? "Submitting..." : scheduledAt ? "Schedule post" : "Publish now"}
      </button>
    </div>
  );
}
