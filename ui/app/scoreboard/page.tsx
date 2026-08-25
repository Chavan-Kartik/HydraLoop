import { Scoreboard } from "@/components/Scoreboard";
import { PageHeader } from "@/components/ui";

export default function ScoreboardPage() {
  return (
    <div>
      <PageHeader
        eyebrow="Defend"
        title="Scoreboard"
        subtitle="Escape rate and archive recall by generation, against the friction budget the defense is allowed to spend, plus the regression gauntlet's verdicts."
      />
      <Scoreboard />
    </div>
  );
}
