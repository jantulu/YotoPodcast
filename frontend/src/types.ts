export type Podcast = {
  id: string;
  name: string;
  rssUrl: string;
};

export type Episode = {
  guid: string;
  title: string;
  published: string;
  enclosureUrl: string;
  mimeType?: string;
};
