export type RootCause = {
  id: string;
  cause: string;
  action: string;
  confidence: "low" | "medium" | "high" | "certain";
};
