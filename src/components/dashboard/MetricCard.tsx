import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MetricEvaluation } from "@/types";

interface MetricCardProps {
  title: string;
  value: number | string | null;
  unit?: string;
  evaluation: MetricEvaluation;
}

export function MetricCard({ title, value, unit, evaluation }: MetricCardProps) {
  const badgeVariant =
    evaluation.status === "Excellent" ? "success" :
    evaluation.status === "Good" ? "success" :
    evaluation.status === "Fair" ? "warning" :
    evaluation.status === "Poor" ? "destructive" :
    evaluation.status === "Informational" ? "informational" :
    evaluation.status === "Warning" ? "warning" : "secondary";

  const displayValue = value === null || value === "" ? "--" : value;

  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <CardTitle className="text-sm font-medium text-gray-500 dark:text-gray-400">
            {title}
          </CardTitle>
          <Badge variant={badgeVariant as any}>{evaluation.status}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline space-x-1">
          <span className="text-2xl font-bold">{displayValue}</span>
          {unit && displayValue !== "--" && (
            <span className="text-sm text-gray-500 dark:text-gray-400">{unit}</span>
          )}
        </div>
        {evaluation.text && (
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            {evaluation.text}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
