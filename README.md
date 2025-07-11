# 北京地铁站点管理系统

## 系统概述

北京地铁站点管理系统是一个综合性地铁信息管理和路径查询平台，提供地铁站点管理、线路规划、路径查询、时刻表管理等功能。系统通过可视化地图界面，让用户可以直观地进行地铁路线查询和规划管理。

## 技术栈

- 前端：HTML5, CSS3, JavaScript, Bootstrap, Mapbox GL JS
- 后端：Python, Flask
- 数据存储：JSON文件

## 启动系统

### 方法一：使用可执行文件

直接双击运行可执行文件启动系统：

```
d:\pythonProject\subway\BeijingSubway.exe
```

这种方式无需安装Python环境，适合所有Windows用户，单文件版本启动时间较长，请耐心等待。

### 方法二：使用Python脚本

如果您已安装Python环境，可以在命令行终端中执行以下命令启动系统：

```bash
cd d:\pythonProject\subway
python app.py
```

系统启动后，默认会在 http://127.0.0.1:5000 运行。

## 系统功能

### 1. 地铁路径查询

- **路径查询**：输入起始站和终点站查询最优路径
- **多维度考量**：考虑距离、时间、换乘次数等因素
- **时间智能化**：自动区分工作日和非工作日时刻表
- **详细行程**：显示详细乘车路线、换乘站点、预计时间等信息

#### 使用方法

1. 访问 http://127.0.0.1:5000
2. 在右侧面板输入起始站点和终点站点
3. 点击"查询路径"按钮
4. 查看查询结果，包括路线详情、换乘信息、票价和时间预估

### 2. 站点管理

#### 添加地铁站点

##### 方法一：通过图形化界面添加

1. 打开浏览器，访问 http://127.0.0.1:5000/edit
2. 点击"添加站点"按钮
3. 在地图上点击选择新站点的位置（经纬度将自动填充）
4. 填写站点名称（如"蓟门桥"）
5. 填写所属线路（如"地铁13号线(西直门--东直门)"）
   - 如果有多条线路，用逗号分隔
6. 选择运营状态（运营中、在建、规划中）
7. 点击"添加站点"按钮提交
8. 添加成功后，系统会显示成功消息
9. 返回主地图查看新添加的站点

##### 方法二：通过API添加

您也可以通过API直接添加站点，示例如下：

```bash
curl -X POST http://127.0.0.1:5000/api/add_station \
  -H "Content-Type: application/json" \
  -d '{
    "station_name": "蓟门桥",
    "lines": ["地铁13号线(西直门--东直门)"],
    "status": "运营中",
    "coordinates": [116.346428, 39.978541]
  }'
```

#### 查找站点

要查找特定站点，可以访问：
http://127.0.0.1:5000/api/find_station?name=站点名称

例如：http://127.0.0.1:5000/api/find_station?name=蓟门桥

#### 删除站点

1. 访问 http://127.0.0.1:5000/edit
2. 点击"删除站点"按钮
3. 从下拉列表中选择要删除的站点
4. 点击"删除站点"按钮确认删除

### 3. 线路管理

#### 添加线路

1. 访问 http://127.0.0.1:5000/edit
2. 点击"添加线路"按钮
3. 填写线路名称（如"地铁1号线(苹果园-四惠)"）
4. 选择线路颜色
5. 设置线路平均速度（km/h）
6. 输入站点序列（空格分隔）
7. 输入相邻站点间距离（米，空格分隔）
8. 输入四种时刻表数据（工作日/非工作日，起始站/终点站）
9. 点击"添加线路"按钮提交

#### 删除线路

1. 访问 http://127.0.0.1:5000/edit
2. 点击"删除线路"按钮
3. 从下拉列表中选择要删除的线路
4. 点击"删除线路"按钮确认删除

## 站点数据格式

每个站点的数据格式如下：

```json
{
  "type": "Feature",
  "properties": {
    "station_name": "站点名称",
    "lines": [
      "地铁X号线(起点--终点)"
    ],
    "status": "运营中",
    "line_size": 1
  },
  "geometry": {
    "type": "Point",
    "coordinates": [
      经度, 纬度
    ]
  }
}
```


