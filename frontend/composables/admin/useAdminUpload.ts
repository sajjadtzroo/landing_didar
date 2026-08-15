// Uploads a file to the admin media endpoint and returns its public URL.
// Used by the landing editor for hero video/poster (and any section image).
export function useAdminUpload() {
  async function upload(file: File): Promise<string> {
    const fd = new FormData()
    fd.append('file', file)
    const res = await apiFetch<{ url: string }>('/admin/media', {
      method: 'POST',
      body: fd,
    })
    return res.url
  }
  return { upload }
}
