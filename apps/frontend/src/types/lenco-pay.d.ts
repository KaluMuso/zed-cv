/** Lenco inline payment widget (https://lenco-api.readme.io/v2.0/reference/accept-payments) */
export interface LencoPayCustomer {
  firstName?: string;
  lastName?: string;
  phone?: string;
}

export interface LencoPayOptions {
  key: string;
  reference: string;
  email: string;
  amount: number;
  currency?: string;
  label?: string;
  channels?: Array<"card" | "mobile-money">;
  customer?: LencoPayCustomer;
  onSuccess?: (response: { reference: string }) => void;
  onClose?: () => void;
  onConfirmationPending?: () => void;
}

export interface LencoPayGlobal {
  getPaid: (options: LencoPayOptions) => void;
}

declare global {
  interface Window {
    LencoPay?: LencoPayGlobal;
    /** Lenco widget reads this for the merchant display name when set before getPaid */
    label?: string;
  }
}

export {};
