const defaultAvatarUrl =
  'https://mmbiz.qpic.cn/mmbiz/icTdbqWNOwNRna42FI242Lcia07jQodd2FJGIYQfG0LAJGFxM4FbnQP6yfMxBgJ0F3YRqJCJ1aPAK2dQagdusBZg/0'

type StoredUserProfile = {
  avatarUrl: string
  nickName: string
}

const STORAGE_KEY_PROFILE = 'ww_user_profile'

function loadStoredProfile(): StoredUserProfile | null {
  const v = wx.getStorageSync(STORAGE_KEY_PROFILE) as unknown
  if (!v || typeof v !== 'object') return null
  const maybe = v as Partial<StoredUserProfile>
  if (!maybe.avatarUrl || !maybe.nickName) return null
  return { avatarUrl: maybe.avatarUrl, nickName: maybe.nickName }
}

function saveStoredProfile(p: StoredUserProfile): void {
  wx.setStorageSync(STORAGE_KEY_PROFILE, p)
}

Component({
  data: {
    userInfo: {
      avatarUrl: defaultAvatarUrl,
      nickName: '',
    },
    hasUserInfo: false,
    canIUseGetUserProfile: wx.canIUse('getUserProfile'),
    canIUseNicknameComp: wx.canIUse('input.type.nickname'),
  },
  lifetimes: {
    attached() {
      const stored = loadStoredProfile()
      if (!stored) return
      this.setData({
        userInfo: stored,
        hasUserInfo: true,
      })
    },
  },
  methods: {
    onChooseAvatar(e: { detail: { avatarUrl: string } }) {
      const { avatarUrl } = e.detail
      const { nickName } = this.data.userInfo
      this.setData({
        'userInfo.avatarUrl': avatarUrl,
        hasUserInfo: Boolean(nickName && avatarUrl && avatarUrl !== defaultAvatarUrl),
      })
      if (nickName && avatarUrl && avatarUrl !== defaultAvatarUrl) {
        saveStoredProfile({ nickName, avatarUrl })
      }
    },
    onInputChange(e: { detail: { value: string } }) {
      const nickName = e.detail.value
      const { avatarUrl } = this.data.userInfo
      this.setData({
        'userInfo.nickName': nickName,
        hasUserInfo: Boolean(nickName && avatarUrl && avatarUrl !== defaultAvatarUrl),
      })
      if (nickName && avatarUrl && avatarUrl !== defaultAvatarUrl) {
        saveStoredProfile({ nickName, avatarUrl })
      }
    },
    getUserProfile() {
      wx.getUserProfile({
        desc: '用于在狼人杀房间中展示你的头像昵称',
        success: (res) => {
          const p: StoredUserProfile = {
            avatarUrl: res.userInfo.avatarUrl,
            nickName: res.userInfo.nickName,
          }
          saveStoredProfile(p)
          this.setData({
            userInfo: p,
            hasUserInfo: true,
          })
        },
      })
    },
    enterClassicRoom() {
      const stored = loadStoredProfile()
      if (!stored) {
        wx.showToast({ title: '请先获取头像昵称', icon: 'none' })
        return
      }
      wx.navigateTo({
        url: `/pages/room/room?roomId=classic`,
      })
    },
  },
})

