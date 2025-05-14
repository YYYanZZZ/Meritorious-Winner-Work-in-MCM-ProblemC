import pandas as pd
import numpy as np
from typing import List

def medal_to_value(medal):
    """
    将奖牌类型转换为数值
    Gold: 15
    Silver: 14
    Bronze: 13
    No Medal: 12
    Not Participated: 11
    """
    if pd.isna(medal):
        return 12  # No Medal
    medal = str(medal).strip()
    if medal == 'Gold':
        return 15
    elif medal == 'Silver':
        return 14
    elif medal == 'Bronze':
        return 13
    return 12  # No Medal

def value_to_medal(value):
    """
    将预测的数值转换回奖牌类型
    15: Gold
    14: Silver
    13: Bronze
    12: No Medal
    11: Not Participated
    """
    if value >= 14.5:
        return 'Gold'
    elif value >= 13.5:
        return 'Silver'
    elif value >= 12.5:
        return 'Bronze'
    elif value >= 11.5:
        return 'No Medal'
    return 'Not Participated'

def get_participation_value(participated_years):
    """
    根据参与年数确定未参与年份的值
    """
    return 11

def gm11(x: List[float], n: int) -> List[float]:
    """
    灰色预测模型 GM(1,1)
    x: 历史数据序列
    n: 需要预测的个数
    return: 预测结果
    """
    # 数据预处理，至少需要4个数据
    x = np.array(x, dtype=float)
    if len(x) < 4:
        return []
    
    # 检查数据是否全为0或只有一个非0值
    if np.sum(x != 0) <= 1:
        return [x[-1]]  # 返回最后一个值
        
    # 为避免0值，对数据进行平移变换
    min_x = np.min(x)
    if min_x == 0:
        x = x + 1  # 所有数据加1，避免0值
    
    # 累加生成
    x1 = np.cumsum(x)
    
    # 生成矩阵B和矩阵Yn
    B = np.zeros((len(x) - 1, 2))
    for i in range(len(x) - 1):
        B[i][0] = -(x1[i] + x1[i + 1]) / 2
        B[i][1] = 1
    Yn = x[1:]
    
    try:
        # 使用最小二乘法计算参数
        B_T = B.T
        B_inverse = np.linalg.inv(B_T.dot(B))
        params = B_inverse.dot(B_T).dot(Yn)
        a, u = params
        
        # 检查参数是否接近0
        if abs(a) < 1e-10:
            return [x[-1]]  # 如果a接近0，返回最后一个值
        
        # 预测未来值
        predictions = []
        x1_hat = []
        
        # 计算x1的预测值
        for k in range(len(x) + n):
            try:
                x1_pred = (x[0] - u/a) * np.exp(-a * k) + u/a
                x1_hat.append(x1_pred)
            except:
                return [x[-1]]  # 如果计算出错，返回最后一个值
        
        # 计算x0的预测值（还原预测值）
        for k in range(1, len(x1_hat)):
            predictions.append(x1_hat[k] - x1_hat[k-1])
        
        # 如果之前进行了平移变换，需要还原
        if min_x == 0:
            predictions = [max(0, p - 1) for p in predictions]
        
        # 只返回需要的预测值
        result = predictions[-n:]
        
        # 确保结果合理
        if any(np.isnan(result)) or any(np.isinf(result)):
            return [x[-1]]
            
        return result
    except:
        return [x[-1]]  # 如果计算过程出错，返回最后一个值

def summarize_team_medals(predictions_df):
    """统计每个队伍的奖牌数"""
    # 创建奖牌统计
    team_medals = predictions_df.groupby('Team').agg({
        'Predicted_Medal': lambda x: list(x)
    }).reset_index()
    
    # 计算每种奖牌的数量
    team_stats = []
    for _, row in team_medals.iterrows():
        medals = row['Predicted_Medal']
        stats = {
            'NOC': row['Team'],  # 改为NOC
            'Gold': medals.count('Gold'),
            'Silver': medals.count('Silver'),
            'Bronze': medals.count('Bronze')
        }
        stats['Total'] = stats['Gold'] + stats['Silver'] + stats['Bronze']
        team_stats.append(stats)
    
    # 创建DataFrame并排序
    team_stats_df = pd.DataFrame(team_stats)
    team_stats_df = team_stats_df.sort_values(['Gold', 'Total'], ascending=[False, False])
    
    return team_stats_df

def allocate_medals_by_event(predictions_df):
    """
    为每个项目分配奖牌，考虑团体项目和个人项目的不同规则
    """
    final_predictions = []
    
    # 按项目分组
    for event, group in predictions_df.groupby('Event'):
        # 判断是否为团体项目
        is_team_event = 'Team' in event
        
        # 按预测分数降序排序
        sorted_athletes = group.sort_values('Prediction_Score', ascending=False).reset_index(drop=True)
        total_athletes = len(sorted_athletes)
        
        # 用于跟踪已分配的奖牌数量
        medals_count = {'Gold': 0, 'Silver': 0, 'Bronze': 0}
        # 用于跟踪已获得奖牌的队伍（团体项目使用）
        teams_with_medals = set()
        
        # 遍历运动员分配奖牌
        for rank, (idx, row) in enumerate(sorted_athletes.iterrows(), 1):
            medal = 'No Medal'
            score = row['Prediction_Score']
            team = row['Team']
            
            if score >= 13:  # 只有达到基本分数要求才可能获得奖牌
                if is_team_event:
                    # 团体项目处理
                    if team not in teams_with_medals:  # 该队伍还未获得奖牌
                        if score >= 14 and medals_count['Gold'] == 0:
                            medal = 'Gold'
                            medals_count['Gold'] = 1
                            teams_with_medals.add(team)
                        elif score >= 13.5 and medals_count['Silver'] == 0:
                            medal = 'Silver'
                            medals_count['Silver'] = 1
                            teams_with_medals.add(team)
                        elif score >= 13 and medals_count['Bronze'] == 0:
                            medal = 'Bronze'
                            medals_count['Bronze'] = 1
                            teams_with_medals.add(team)
                else:
                    # 个人项目处理
                    if score >= 14 and medals_count['Gold'] < 1:
                        medal = 'Gold'
                        medals_count['Gold'] += 1
                    elif score >= 13.5 and medals_count['Silver'] < 1:
                        medal = 'Silver'
                        medals_count['Silver'] += 1
                    elif score >= 13 and medals_count['Bronze'] < 1:
                        medal = 'Bronze'
                        medals_count['Bronze'] += 1
            else:
                medal = 'Not Participated' if score < 12 else 'No Medal'
            
            # 创建预测结果
            final_predictions.append({
                'Name': row['Name'],
                'Event': row['Event'],
                'Team': team,
                'Year': 2028,
                'Predicted_Medal': medal,
                'Prediction_Score': score,
                'History_Data': row['History_Data'],
                'Participation_Count': row['Participation_Count'],
                'Original_Score': score,
                'Rank_In_Event': rank,
                'Total_Athletes': total_athletes,
                'Is_Team_Event': is_team_event
            })
    
    return pd.DataFrame(final_predictions)

def process_and_predict():
    # 读取处理好的数据
    df = pd.read_csv('evaluation21.csv')
    print("加载数据形状:", df.shape)
    
    # 创建新的DataFrame来存储预测结果
    predictions = []
    
    # 按运动员和项目分组
    groups = df.groupby(['Name', 'Event'])
    print(f"总共分组数量: {len(groups)}")
    
    # 记录不同情况的计数
    total_groups = 0
    prediction_failed = 0
    prediction_success = 0
    
    # 要考虑的年份列表
    years = [2012, 2016, 2020, 2024]
    
    # 按运动员和项目分组
    for (name, event), group in groups:
        total_groups += 1
        
        # 获取最新的Team信息
        latest_team = group.iloc[-1]['Team']
        
        # 创建完整的历史记录（包含所有年份）
        history = []
        group_years = group['Year'].tolist()
        participated_count = len(group_years)  # 统计参与次数
        
        # 对每个年份，检查是否有参赛记录
        for year in years:
            if year in group_years:
                # 获取该年的奖牌值
                medal = group[group['Year'] == year]['Medal'].iloc[0]
                value = medal_to_value(medal)
            else:
                # 根据参与次数设置未参与年份的值
                value = get_participation_value(participated_count)
            history.append(value)
            
        # 打印调试信息
        if total_groups % 1000 == 0:
            print(f"\n处理第 {total_groups} 组:")
            print(f"运动员: {name}")
            print(f"项目: {event}")
            print(f"队伍: {latest_team}")
            print(f"参与次数: {participated_count}")
            print(f"历史数据: {history}")
        
        # 使用灰色预测模型预测2028年结果
        pred = gm11(history, 1)
        
        if len(pred) > 0:
            pred_value = pred[0]
            # 确保预测值在合理范围内
            pred_value = max(11, min(15, pred_value))  # 11-15之间
            # 将预测值转换为奖牌类型
            medal_pred = value_to_medal(pred_value)
            
            # 保存预测结果
            predictions.append({
                'Name': name,
                'Event': event,
                'Team': latest_team,
                'Year': 2028,
                'Predicted_Medal': medal_pred,
                'Prediction_Score': pred_value,
                'History_Data': str(history),
                'Participation_Count': participated_count  # 添加参与次数信息
            })
            prediction_success += 1
        else:
            prediction_failed += 1
    
    # 打印统计信息
    print("\n预测统计信息:")
    print(f"总分组数: {total_groups}")
    print(f"预测失败组数: {prediction_failed}")
    print(f"预测成功组数: {prediction_success}")
    
    # 创建预测结果DataFrame
    predictions_df = pd.DataFrame(predictions)
    print("\n初始预测结果形状:", predictions_df.shape)
    
    # 对每个项目重新分配奖牌
    final_predictions_df = allocate_medals_by_event(predictions_df)
    print("\n重新分配奖牌后的结果形状:", final_predictions_df.shape)
    print("\n预测结果示例:")
    print(final_predictions_df.head())
    
    # 保存预测结果（添加错误处理）
    try:
        predictions_file = 'predictions_2028_new.csv'
        final_predictions_df.to_csv(predictions_file, index=False)
        print(f"\n预测结果已保存到 {predictions_file}")
    except Exception as e:
        print(f"\n保存预测结果时出错: {e}")
        predictions_file = 'predictions_2028_backup.csv'
        try:
            final_predictions_df.to_csv(predictions_file, index=False)
            print(f"预测结果已保存到备用文件: {predictions_file}")
        except Exception as e:
            print(f"保存到备用文件也失败: {e}")
    
    # 生成队伍奖牌统计
    team_stats = summarize_team_medals(final_predictions_df)
    print("\n队伍奖牌统计:")
    print(team_stats.head(10))  # 显示前10名
    
    # 保存队伍统计结果（添加错误处理）
    try:
        team_stats_file = 'team_medals_2028_new.csv'
        team_stats.to_csv(team_stats_file)
        print(f"\n队伍奖牌统计已保存到 {team_stats_file}")
    except Exception as e:
        print(f"\n保存队伍统计时出错: {e}")
        team_stats_file = 'team_medals_2028_backup.csv'
        try:
            team_stats.to_csv(team_stats_file)
            print(f"队伍统计已保存到备用文件: {team_stats_file}")
        except Exception as e:
            print(f"保存到备用文件也失败: {e}")
    
    return final_predictions_df, team_stats

def process_medal_counts():
    """处理并返回国家奖牌统计数据"""
    try:
        # 运行预测获取结果
        _, team_stats = process_and_predict()
        
        # 确保包含所需的列
        if 'NOC' not in team_stats.columns:
            print("警告：需要重新生成团队统计")
            # 重新生成正确格式的团队统计
            predictions_df, _ = process_and_predict()
            team_stats = summarize_team_medals(predictions_df)
        
        # 确保列名正确
        required_columns = ['NOC', 'Gold', 'Silver', 'Bronze', 'Total']
        if not all(col in team_stats.columns for col in required_columns):
            raise ValueError(f"缺少必要的列: {required_columns}")
        
        # 只选择需要的列
        team_stats = team_stats[required_columns]
        
        return team_stats
        
    except Exception as e:
        print(f"处理奖牌统计时出错: {e}")
        return pd.DataFrame(columns=['NOC', 'Gold', 'Silver', 'Bronze', 'Total'])  # 返回空DataFrame但包含正确的列

if __name__ == "__main__":
    try:
        # 运行预测
        predictions, team_stats = process_and_predict()
        print("预测完成")
    except Exception as e:
        print(f"运行过程中出错: {e}")
