export type Podcast = {
  slug: string;
  title: string;
  feedUrl: string;
};

export type Episode = {
  id: string;
  title: string;
  audioUrl: string;
};

export type AuthStart = {
  verification_uri_complete?: string;
  verification_uri?: string;
  user_code?: string;
  interval?: number;
  expires_in?: number;
};

export type AuthStatus =
  | { authenticated: true; expires_at: number }
  | { pending: true; verification_uri_complete?: string; verification_uri?: string; user_code?: string; interval?: number }
  | { authenticated: false; error?: string };

export type UploadResult = {
  uploadId: string;
  transcoded: any;
};
