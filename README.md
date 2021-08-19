#介绍
自动从教务获取课表并生成`.ics`日历文件的Python脚本
#用法
`python main.py -s 学号 -d 课表开始日期`

根据提示输入教务网站密码后，就可生成`timetable.ics`日历文件
#依赖
- requests
#已知问题
无法处理单双周，目前已知“控制系统设计与仿真”存在该问题，会在第5周（单周）多出一节课。
#鸣谢
- [PyRsa](https://github.com/hibiscustoyou/pyrsa)