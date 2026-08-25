import { Governance } from "@/components/Governance";
import { PageHeader } from "@/components/ui";

export default function GovernancePage() {
  return (
    <div>
      <PageHeader
        eyebrow="Responsible AI"
        title="Governance & Audit"
        subtitle="Every generation is recorded in an append-only, hash-chained ledger. Re-verify on stage to prove the run history has not been altered."
      />
      <Governance />
    </div>
  );
}
