import { useMemo, useState } from "react";

import { ResultCard } from "@/components/ResultCard";
import type { SearchResult } from "@/lib/api";
import { searchItems, sendFeedback } from "@/lib/api";

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [grade, setGrade] = useState("");
  const [source, setSource] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [queryId, setQueryId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);

  const canSearch = useMemo(() => query.trim().length > 0, [query]);

  const handleSearch = async () => {
    if (!canSearch) {
      setError("请输入查询关键词。");
      return;
    }

    setLoading(true);
    setError(null);
    setFeedbackMessage(null);

    try {
      const response = await searchItems({
        query: query.trim(),
        top_n: 10,
        meta_filters: {
          ...(grade ? { grade } : {}),
          ...(source ? { source } : {}),
        },
      });
      setResults(response.results);
      setQueryId(response.query_id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "搜索失败";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (itemId: string, vote: 1 | -1) => {
    if (!queryId) {
      setFeedbackMessage("请先执行搜索后再反馈。");
      return;
    }

    try {
      await sendFeedback({ query_id: queryId, item_id: itemId, vote });
      setFeedbackMessage(vote === 1 ? "感谢反馈：已记录为有帮助。" : "感谢反馈：已记录为不相关。");
    } catch (err) {
      const message = err instanceof Error ? err.message : "反馈提交失败";
      setFeedbackMessage(message);
    }
  };

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#f8fafc",
        padding: "32px 16px 64px",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        color: "#0f172a",
      }}
    >
      <section style={{ maxWidth: 980, margin: "0 auto", display: "flex", flexDirection: "column", gap: 20 }}>
        <header style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <h1 style={{ margin: 0, fontSize: 28 }}>Memory Search MVP</h1>
          <p style={{ margin: 0, color: "#64748b" }}>
            输入模糊描述，系统将返回相关题目，并展示命中证据片段。
          </p>
        </header>

        <div
          style={{
            background: "#fff",
            borderRadius: 16,
            padding: 20,
            border: "1px solid #e2e8f0",
            display: "grid",
            gridTemplateColumns: "1fr",
            gap: 12,
          }}
        >
          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontWeight: 600 }}>查询内容</span>
            <textarea
              rows={3}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="例如：浙江2019 解析几何 最值 重心 分式 韦达"
              style={{
                borderRadius: 12,
                border: "1px solid #cbd5f5",
                padding: 12,
                fontSize: 14,
                resize: "vertical",
              }}
            />
          </label>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <span style={{ fontWeight: 600 }}>年级（可选）</span>
              <input
                value={grade}
                onChange={(event) => setGrade(event.target.value)}
                placeholder="高中"
                style={{
                  borderRadius: 12,
                  border: "1px solid #cbd5f5",
                  padding: "10px 12px",
                }}
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <span style={{ fontWeight: 600 }}>来源（可选）</span>
              <input
                value={source}
                onChange={(event) => setSource(event.target.value)}
                placeholder="真题"
                style={{
                  borderRadius: 12,
                  border: "1px solid #cbd5f5",
                  padding: "10px 12px",
                }}
              />
            </label>
          </div>

          <button
            type="button"
            onClick={handleSearch}
            disabled={loading}
            style={{
              alignSelf: "flex-start",
              borderRadius: 999,
              border: "none",
              background: loading ? "#94a3b8" : "#2563eb",
              color: "#fff",
              padding: "10px 20px",
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "搜索中..." : "开始搜索"}
          </button>

          {error && <div style={{ color: "#dc2626" }}>{error}</div>}
          {feedbackMessage && <div style={{ color: "#0f766e" }}>{feedbackMessage}</div>}
        </div>

        <section style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <h2 style={{ margin: 0, fontSize: 20 }}>检索结果</h2>
            <span style={{ color: "#64748b" }}>{results.length} 条</span>
          </div>

          {results.length === 0 ? (
            <div style={{
              background: "#fff",
              border: "1px dashed #cbd5f5",
              borderRadius: 12,
              padding: 20,
              color: "#94a3b8",
            }}>
              暂无结果，请输入关键词后搜索。
            </div>
          ) : (
            <div style={{ display: "grid", gap: 16 }}>
              {results.map((result) => (
                <ResultCard key={result.item_id} result={result} onFeedback={handleFeedback} />
              ))}
            </div>
          )}
        </section>
      </section>
    </main>
  );
}
