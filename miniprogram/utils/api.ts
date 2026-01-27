import {BACKEND_BASE_URL} from '../config'

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE'

export type ApiRequestOptions<TData> = {
  method: HttpMethod
  path: string
  data?: TData
  timeoutMs?: number
}

export function request<TResponse, TData = unknown>(opts: ApiRequestOptions<TData>): Promise<TResponse> {
  return new Promise<TResponse>((resolve, reject) => {
    console.log(`[request] 开始请求: ${opts.method} ${opts.path}`)
    const requestData = (opts.data as any) || undefined
    wx.request({
      url: `${BACKEND_BASE_URL}${opts.path}`,
      method: opts.method as any,
      data: requestData,
      timeout: opts.timeoutMs ?? 10_000,
      header: {
        'content-type': 'application/json',
      },
      success: (res) => {
        const { statusCode, data } = res
        console.log(`[request] 收到响应: statusCode=${statusCode}`)
        console.log(`[request] 原始响应数据:`, data)

        if (statusCode >= 200 && statusCode < 300) {
          // 后端返回标准格式 { code, message, data }，提取 data 字段
          if (data && typeof data === 'object' && 'data' in data) {
            console.log(`[request] 提取响应中的 data 字段`)
            resolve((data as any).data as TResponse)
            return
          }

          // 直接返回响应数据
          console.log(`[request] 直接返回响应数据`)
          resolve(data as TResponse)
          return
        }
        console.log(`[request] 错误: HTTP ${statusCode}`)
        reject(new Error(`HTTP ${statusCode}`))
      },
      fail: (err) => {
        console.log(`[request] 请求失败:`, err)
        reject(err)
      },
    })
  })
}

