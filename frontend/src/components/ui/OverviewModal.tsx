import { X, BookOpen, ExternalLink, Zap } from "lucide-react";
import { useEffect } from "react";
import { ContentItem } from "../../api/agent";

interface OverviewModalProps {
  item: ContentItem;
  onClose: () => void;
}

export function OverviewModal({ item, onClose }: OverviewModalProps) {
  // Prevent body scrolling when the modal is open
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "auto";
    };
  }, []);

  return (
    <div 
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 sm:p-6 bg-black/70 backdrop-blur-sm animate-fade-in" 
      onClick={onClose}
    >
      <div 
        className="bg-[#0f111a] border border-white/10 rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl animate-scale-in" 
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 sm:p-5 border-b border-white/10 bg-white/[0.02] shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-brand-500/20">
              <BookOpen size={18} className="text-brand-300" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white leading-tight">News Overview</h3>
              <p className="text-xs text-white/40">{item.source_label}</p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="p-2 text-white/40 hover:text-white hover:bg-white/10 rounded-xl transition-all"
          >
            <X size={18} />
          </button>
        </div>
        
        {/* Scrollable Content */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-6 flex-1 custom-scrollbar">
          <div>
            <a 
              href={item.source_url || "#"} 
              target="_blank" 
              rel="noreferrer" 
              className="text-lg font-semibold text-white/90 hover:text-white flex items-start gap-2 mb-4 leading-snug group"
            >
              {item.title} <ExternalLink size={14} className="shrink-0 mt-1.5 text-white/30 group-hover:text-white/60 transition-colors" />
            </a>
            
            <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5 shadow-inner">
              <p className="text-sm sm:text-base text-white/80 leading-relaxed whitespace-pre-wrap">
                {item.summary || item.raw_content || "No extended overview is available for this item. This typically happens for link-only posts before clicking 'Collect now'."}
              </p>
            </div>
          </div>

          {item.key_points && item.key_points.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-3">Key Takeaways</h4>
              <ul className="space-y-3">
                {item.key_points.map((pt, i) => (
                  <li key={i} className="text-sm text-white/70 flex gap-3 bg-white/[0.02] p-3 rounded-xl border border-white/[0.04]">
                    <span className="text-brand-400 font-bold shrink-0 mt-0.5">•</span>
                    <span className="leading-relaxed">{pt}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {item.suggested_angle && (
            <div>
              <h4 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-3 flex items-center gap-2">
                <Zap size={12} className="text-amber-400"/> Recommended Content Angle
              </h4>
              <p className="text-sm text-amber-300/90 leading-relaxed bg-amber-500/10 p-5 rounded-xl border border-amber-500/20 shadow-inner">
                {item.suggested_angle}
              </p>
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="p-4 sm:p-5 border-t border-white/10 bg-white/[0.02] flex justify-end shrink-0">
          <button 
            onClick={onClose} 
            className="px-6 py-2.5 text-sm font-semibold text-white border border-white/10 hover:bg-white/10 rounded-xl transition-all"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
