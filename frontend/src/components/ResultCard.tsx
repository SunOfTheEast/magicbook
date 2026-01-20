import type { SearchResult } from "@/lib/api";

export type ResultCardProps = {
  result: SearchResult;
  onFeedback: (itemId: string, vote: 1 | -1) => void;
};

const viewTypeLabels: Record<string, string> = {
  problem: "题干",
  diagram: "图示",
  method: "方法链",
  note: "批注",
  solution_outline: "提纲",
};

export function ResultCard({ result, onFeedback }: ResultCardProps) {
  return (
    <article
      style={{
        border: "1px solid #e2e8f0",
        borderRadius: 12,
        padding: 16,
        background: "#fff",
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <header style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 18 }}>{result.title || "未命名题目"}</h3>
          <div style={{ color: "#64748b", fontSize: 13 }}>匹配得分：{result.score.toFixed(2)}</div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="button"
            onClick={() => onFeedback(result.item_id, 1)}
            style={{
              borderRadius: 999,
              border: "1px solid #cbd5f5",
              padding: "6px 12px",
              background: "#eef2ff",
              cursor: "pointer",
            }}
          >
            👍 有帮助
          </button>
          <button
            type="button"
            onClick={() => onFeedback(result.item_id, -1)}
            style={{
              borderRadius: 999,
              border: "1px solid #fecaca",
              padding: "6px 12px",
              background: "#fef2f2",
              cursor: "pointer",
            }}
          >
            👎 不相关
          </button>
        </div>
      </header>

      <section style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <strong>命中证据</strong>
        {result.evidence.length === 0 ? (
          <div style={{ color: "#94a3b8" }}>暂无证据片段</div>
        ) : (
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {result.evidence.map((evidence) => (
              <li key={`${result.item_id}-${evidence.view_type}-${evidence.rank}`}>
                <span style={{ color: "#2563eb", fontWeight: 600 }}>
                  {viewTypeLabels[evidence.view_type] ?? evidence.view_type}
                </span>
                ：<span dangerouslySetInnerHTML={{ __html: evidence.snippet }} />
              </li>
            ))}
          </ul>
        )}
      </section>

      {result.user_tags.length > 0 && (
        <section style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {result.user_tags.map((tag) => (
            <span
              key={`${result.item_id}-${tag}`}
              style={{
                fontSize: 12,
                color: "#334155",
                background: "#f1f5f9",
                borderRadius: 999,
                padding: "4px 8px",
              }}
            >
              {tag}
            </span>
          ))}
        </section>
      )}
    </article>
  );
}
