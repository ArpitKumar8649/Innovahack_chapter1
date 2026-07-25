import { useState } from "react";
import type { Claim } from "../../types";

interface ExpertFlagButtonProps {
  runId: string;
  claim: Claim;
}

/**
 * ExpertFlagButton — allows domain experts to flag verdicts for review.
 * Flags can be converted into harness test cases.
 */
export function ExpertFlagButton({ runId, claim }: ExpertFlagButtonProps) {
  const [showForm, setShowForm] = useState(false);
  const [expertName, setExpertName] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async () => {
    if (!expertName.trim() || !reason.trim()) return;

    setSubmitting(true);
    try {
      const res = await fetch("/api/flag", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          run_id: runId,
          claim_id: claim.id,
          expert_name: expertName,
          reason,
        }),
      });

      if (res.ok) {
        setSubmitted(true);
        setShowForm(false);
        setExpertName("");
        setReason("");
      }
    } catch (err) {
      console.error("Failed to submit flag:", err);
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return <span className="flag-submitted">✓ Flagged</span>;
  }

  if (!showForm) {
    return (
      <button
        className="flag-button mono"
        onClick={() => setShowForm(true)}
        title="Flag this verdict for expert review"
      >
        ⚑ Flag
      </button>
    );
  }

  return (
    <div className="flag-form">
      <input
        type="text"
        placeholder="Your name"
        value={expertName}
        onChange={(e) => setExpertName(e.target.value)}
        className="flag-input"
        disabled={submitting}
      />
      <textarea
        placeholder="Reason for flagging..."
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        className="flag-textarea"
        rows={3}
        disabled={submitting}
      />
      <div className="flag-actions">
        <button
          className="flag-submit"
          onClick={handleSubmit}
          disabled={submitting || !expertName.trim() || !reason.trim()}
        >
          {submitting ? "Submitting..." : "Submit Flag"}
        </button>
        <button
          className="flag-cancel"
          onClick={() => setShowForm(false)}
          disabled={submitting}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
