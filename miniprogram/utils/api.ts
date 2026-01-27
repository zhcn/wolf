import {BACKEND_BASE_URL} from '../config'

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export type ApiRequestOptions<TData> = {
  method: HttpMethod
  path: string
  data?: TData
  timeoutMs?: number
}

export function request<TResponse, TData = unknown>(opts: ApiRequestOptions<TData>): Promise<TResponse> {
  return new Promise<TResponse>((resolve, reject) => {
    console.log(`[request] 开始请求: ${opts.method} ${opts.path}`)
    wx.request({
      url: `${BACKEND_BASE_URL}${opts.path}`,
      method: opts.method,
      data: opts.data,
      timeout: opts.timeoutMs ?? 10_000,
      header: {
        'content-type': 'application/json',
      },
      success: (res) => {
        const { statusCode, data } = res
        console.log(`[request] 收到响应: statusCode=${statusCode}`)
        console.log(`[request] 响应数据类型: ${typeof data}`)
        console.log(`[request] 响应数据 keys: ${data && typeof data === 'object' ? Object.keys(data as any).join(',') : 'N/A'}`)
        console.log(`[request] 原始响应数据:`, data)

        if (statusCode >= 200 && statusCode < 300) {
          // 处理后端标准响应格式 { code, message, data }
          // 如果响应中有 code 字段且同时有 data 字段，说明是标准格式
          console.log(`[request] 检查是否是标准格式...`)
          const hasCode = data && typeof data === 'object' && 'code' in data
          const hasData = data && typeof data === 'object' && 'data' in data
          const innerDataIsObject = hasData && typeof (data as any).data === 'object'

          console.log(`[request] hasCode: ${hasCode}, hasData: ${hasData}, innerDataIsObject: ${innerDataIsObject}`)

          if (hasCode && hasData && innerDataIsObject) {
            console.log(`[request] 检测到标准格式，提取内层 data`)
            const innerData = (data as any).data
            console.log(`[request] 内层 data:`, innerData)
            resolve(innerData as TResponse)
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

