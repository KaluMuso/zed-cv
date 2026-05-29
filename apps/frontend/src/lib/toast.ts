import { toast } from "sonner";

export const notify = {
  saved: (label = "Job saved") => toast.success(label),
  unsaved: (label = "Removed from saved") => toast.error(label),
  success: (label: string) => toast.success(label),
  payment: (label: string) => toast.success(label),
  info: (label: string) => toast.info(label),
  error: (label: string) => toast.error(label),
  loading: (label: string) => toast.loading(label),
  custom: toast,
};
