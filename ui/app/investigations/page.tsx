import { Investigations } from "@/components/Investigations";
import { PageHeader } from "@/components/ui";

export default function InvestigationsPage() {
  return (
    <div>
      <PageHeader
        eyebrow="Defend"
        title="Investigation View"
        subtitle="Analyst-facing explanations for the latest lab episode: SHAP reason codes plus a counterfactual. Run the Lab first if this is empty."
      />
      <Investigations />
    </div>
  );
}
